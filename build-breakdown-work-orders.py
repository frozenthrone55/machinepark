from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="breakdown-work-orders-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    # De bestaande werkboneditor is bewust generiek genoeg voor elk toestel.
    # Exporteer alleen de twee helpers die de depannage-integratie nodig heeft.
    replace_once(
        "  window.machineparkWorkOrderDetailsHtml = workOrderDetailsHtml;",
        "  window.machineparkWorkOrderDetailsHtml = workOrderDetailsHtml;\n  window.machineparkMakeWorkOrderEditor = makeWorkOrderEditor;\n  window.machineparkCollectWorkOrder = collectWorkOrder;",
        "werkbonhelpers exporteren",
    )

    # Werkbon ook in de depannage-gebeurtenis van de toesteltijdlijn.
    replace_once(
        "</p>${deviceTimelinePhotosHtml(b.photos,'Depannagefoto')}",
        "</p>${workOrderTimelineHtml(b.workOrder)}${deviceTimelinePhotosHtml(b.photos,'Depannagefoto')}",
        "depannagewerkbon in toesteltijdlijn",
    )

    # Voeg de depannagekoppeling in dezelfde runtime toe als de bestaande werkbonmodule.
    anchor = "  const baseOpenMaintenanceForWorkOrders = openMaintenance;"
    feature = r'''  function attachBreakdownWorkOrders(existingId = '') {
    const modal = document.querySelector('#modal .modal-body');
    if (!modal || typeof window.machineparkMakeWorkOrderEditor !== 'function') return;
    const cards = [...modal.querySelectorAll('.breakdown-machine-card')];
    if (cards.length) {
      cards.forEach((card) => {
        if (card.querySelector('[data-workorder-editor]')) return;
        const deviceId = card.dataset?.breakdownDevice || '';
        const device = state.devices.find((item) => item.id === deviceId) || {};
        const fields = card.querySelector('.maintenance-machine-fields') || card;
        const editor = window.machineparkMakeWorkOrderEditor(device, null);
        const photoEditor = fields.querySelector('.service-photo-editor');
        if (photoEditor) fields.insertBefore(editor, photoEditor);
        else fields.appendChild(editor);
        const enabled = card.classList.contains('selected');
        editor.querySelectorAll('input,select,textarea').forEach((el) => { el.disabled = !enabled; });
      });
      return;
    }
    if (!existingId || modal.querySelector('[data-workorder-editor]')) return;
    const record = state.breakdowns.find((item) => item.id === existingId) || null;
    const device = state.devices.find((item) => item.id === record?.deviceId) || {};
    const grid = modal.querySelector('.form-grid') || modal;
    const editor = window.machineparkMakeWorkOrderEditor(device, record?.workOrder || null);
    const photoField = grid.querySelector('.service-photo-editor')?.closest('.field');
    if (photoField) grid.insertBefore(editor, photoField);
    else grid.appendChild(editor);
  }

  function validateBreakdownWorkOrders(existingId = '') {
    if (typeof window.machineparkCollectWorkOrder !== 'function') return;
    if (existingId) {
      const editor = document.querySelector('#modal [data-workorder-editor]');
      if (editor) window.machineparkCollectWorkOrder(editor);
      return;
    }
    [...document.querySelectorAll('#modal .breakdown-machine-card.selected')].forEach((card) => {
      const editor = card.querySelector('[data-workorder-editor]');
      if (editor) window.machineparkCollectWorkOrder(editor);
    });
  }

  function installBreakdownWorkOrderValidation(existingId = '') {
    const form = document.getElementById('modalForm');
    if (!form || form._breakdownWorkOrderValidation) return;
    form.addEventListener('submit', (event) => {
      try { validateBreakdownWorkOrders(existingId); }
      catch (error) {
        event.preventDefault();
        event.stopImmediatePropagation();
        alert(error?.message || 'Controleer de werkbon.');
      }
    }, true);
    form._breakdownWorkOrderValidation = true;
  }

  const baseSetBreakdownMachineEnabledForWorkOrders = setBreakdownMachineEnabled;
  setBreakdownMachineEnabled = function(card, enabled) {
    baseSetBreakdownMachineEnabledForWorkOrders(card, enabled);
    card?.querySelectorAll('[data-workorder-editor] input,[data-workorder-editor] select,[data-workorder-editor] textarea').forEach((el) => { el.disabled = !enabled; });
  };
  window.setBreakdownMachineEnabled = setBreakdownMachineEnabled;

  const baseBreakdownBatchSelectedItemsForWorkOrders = breakdownBatchSelectedItems;
  breakdownBatchSelectedItems = function() {
    const items = baseBreakdownBatchSelectedItemsForWorkOrders();
    return items.map((item) => {
      const card = [...document.querySelectorAll('#modal .breakdown-machine-card')].find((candidate) => candidate.dataset?.breakdownDevice === item.deviceId);
      const editor = card?.querySelector('[data-workorder-editor]');
      return editor && typeof window.machineparkCollectWorkOrder === 'function'
        ? { ...item, workOrder: window.machineparkCollectWorkOrder(editor) }
        : item;
    });
  };
  window.breakdownBatchSelectedItems = breakdownBatchSelectedItems;

  const baseOpenBreakdownForWorkOrders = openBreakdown;
  openBreakdown = function(id) {
    const result = baseOpenBreakdownForWorkOrders(id);
    window.machineparkLoadWorkOrderTemplates?.().then(() => {
      const installWorkOrders = () => {
        attachBreakdownWorkOrders(id || '');
        installBreakdownWorkOrderValidation(id || '');
        const modal = document.querySelector('#modal .modal-body');
        const box = modal?.querySelector('#breakdownLocationDevices');
        if (box && !box._breakdownWorkOrderObserver) {
          const observer = new MutationObserver(() => attachBreakdownWorkOrders(id || ''));
          observer.observe(box, { childList:true });
          box._breakdownWorkOrderObserver = observer;
        }
      };
      setTimeout(installWorkOrders, 0);
      setTimeout(installWorkOrders, 100);
    }).catch((error) => console.warn('Werkbonnen laden voor depannage', error));
    return result;
  };
  window.openBreakdown = openBreakdown;

'''
    replace_once(anchor, feature + anchor, "depannagewerkbonruntime")

    # De bestaande opslagwrapper voor onderhoud blijft intact. Deze tweede wrapper
    # voegt de gekozen werkbon toe aan één of meerdere depannageregistraties.
    storage_anchor = "  const baseShowMaintenanceDetailsForWorkOrders = showMaintenanceDetails;"
    storage_feature = r'''  const basePutBreakdownForWorkOrders = put;
  put = async function(storeName, obj) {
    if (storeName === 'breakdowns' && obj) {
      const cards = [...document.querySelectorAll('#modal .breakdown-machine-card')];
      if (!cards.length) {
        const editor = document.querySelector('#modal [data-workorder-editor]');
        if (editor && typeof window.machineparkCollectWorkOrder === 'function') obj = { ...obj, workOrder: window.machineparkCollectWorkOrder(editor) };
      }
    }
    return basePutBreakdownForWorkOrders(storeName, obj);
  };
  window.put = put;

  const basePutManyBreakdownForWorkOrders = putMany;
  putMany = async function(storeName, items) {
    if (storeName === 'breakdowns' && Array.isArray(items)) {
      items = items.map((item) => {
        const card = [...document.querySelectorAll('#modal .breakdown-machine-card')].find((candidate) => candidate.dataset?.breakdownDevice === item.deviceId);
        const editor = card?.querySelector('[data-workorder-editor]');
        return editor && typeof window.machineparkCollectWorkOrder === 'function'
          ? { ...item, workOrder: window.machineparkCollectWorkOrder(editor) }
          : item;
      });
    }
    return basePutManyBreakdownForWorkOrders(storeName, items);
  };
  window.putMany = putMany;

'''
    replace_once(storage_anchor, storage_feature + storage_anchor, "depannagewerkbonopslag")

    # Werkbon in de bestaande depannagedetailweergave tonen.
    details_anchor = "  function ensureSettingsCard() {"
    details_feature = r'''  const baseShowBreakdownDetailsForWorkOrders = window.machineparkShowBreakdownDetails;
  if (typeof baseShowBreakdownDetailsForWorkOrders === 'function') {
    window.machineparkShowBreakdownDetails = function(id) {
      const result = baseShowBreakdownDetailsForWorkOrders(id);
      setTimeout(() => {
        const record = state.breakdowns.find((item) => item.id === id);
        const grid = document.querySelector('#modal .breakdown-detail-summary');
        if (!record || !grid || grid.querySelector('.workorder-detail-block')) return;
        const block = document.createElement('div');
        block.className = 'breakdown-detail-field full workorder-detail-block';
        block.innerHTML = `<label>Werkbon</label><div class="value">${window.machineparkWorkOrderDetailsHtml?.(record.workOrder) || '<span class="muted">Geen werkbon gekoppeld.</span>'}</div>`;
        const photos = [...grid.children].find((child) => child.querySelector?.('.breakdown-detail-photos'));
        if (photos) grid.insertBefore(block, photos);
        else grid.appendChild(block);
      }, 0);
      return result;
    };
  }

'''
    replace_once(details_anchor, details_feature + details_anchor, "depannagewerkbon in details")

    # Concepten: werkbon bij depannage mee autosaven, herstellen en valideren.
    replace_once(
        "        record.solution = card.querySelector('.breakdown-machine-solution')?.value.trim() || '';",
        "        record.solution = card.querySelector('.breakdown-machine-solution')?.value.trim() || '';\n        record.workOrder = collectWorkOrderLoose(card, old?.workOrder || null);",
        "depannagewerkbon in concept bewaren",
    )
    replace_once(
        "        if (kind === 'maintenance') restoreWorkOrder(card, item.workOrder, enabled);\n        else restoreFaultRef(card, item.faultRef);",
        "        if (kind === 'maintenance') restoreWorkOrder(card, item.workOrder, enabled);\n        else { restoreWorkOrder(card, item.workOrder, enabled); restoreFaultRef(card, item.faultRef); }",
        "depannagewerkbon uit concept herstellen",
    )
    replace_once(
        "      if (missing) throw new Error(`Vul het probleem / de melding in voor ${deviceName(missing.deviceId) || 'elk geselecteerd toestel'}.`);\n    } else selected.forEach(item => validateWorkOrder(item.workOrder));",
        "      if (missing) throw new Error(`Vul het probleem / de melding in voor ${deviceName(missing.deviceId) || 'elk geselecteerd toestel'}.`);\n      selected.forEach(item => validateWorkOrder(item.workOrder));\n    } else selected.forEach(item => validateWorkOrder(item.workOrder));",
        "depannagewerkbon bij concept afronden valideren",
    )

    # Marker na alle scripts zodat de audit eenvoudig kan aantonen dat de patch draaide.
    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor depannagewerkbon')
    index = index[:pos] + f'<span {MARKER} hidden></span>\n' + index[pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'window.machineparkMakeWorkOrderEditor = makeWorkOrderEditor',
    'function attachBreakdownWorkOrders',
    "candidate.dataset?.breakdownDevice === item.deviceId",
    "storeName === 'breakdowns'",
    'baseOpenBreakdownForWorkOrders',
    'baseShowBreakdownDetailsForWorkOrders',
    "workOrderTimelineHtml(b.workOrder)",
    "record.workOrder = collectWorkOrderLoose(card, old?.workOrder || null)",
    "restoreWorkOrder(card, item.workOrder, enabled); restoreFaultRef(card, item.faultRef)",
    "selected.forEach(item => validateWorkOrder(item.workOrder))",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: depannagewerkbon ontbreekt ({needle})')

print('[Machinepark] werkbonnen zijn per toestel beschikbaar bij depannages, details, tijdlijn, print en concepten')
