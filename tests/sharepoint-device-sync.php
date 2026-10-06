<?php
declare(strict_types=1);
$dir=sys_get_temp_dir().'/mp-sync-test-'.bin2hex(random_bytes(5));mkdir($dir);mkdir($dir.'/backups');
define('MP_DATA_DIR',$dir);define('MP_BACKUP_DIR',$dir.'/backups');define('MP_STATE_FILE',$dir.'/state-v1.json');define('MP_LOCK_FILE',$dir.'/state-v1.lock');
require_once __DIR__.'/../synology/api/_device-sync-lib.php';
function check($ok,$why){if(!$ok)throw new RuntimeException($why);}
try {
    $zip=new ZipArchive();$file=$dir.'/fixture.xlsx';$zip->open($file,ZipArchive::CREATE);
    $zip->addFromString('xl/sharedStrings.xml','<sst><si><t>WCL NR.</t></si><si><t>ZAAKNAAM</t></si><si><t>WCL0001</t></si></sst>');
    $zip->addFromString('xl/styles.xml','<styleSheet><fills><fill/><fill><patternFill><fgColor rgb="FFFF6666"/></patternFill></fill></fills><cellXfs><xf fillId="0"/><xf fillId="1"/></cellXfs></styleSheet>');
    $zip->addFromString('xl/worksheets/sheet2.xml','<worksheet><sheetData><row><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row><row><c r="A2" t="s" s="1"><v>2</v></c><c r="B2" t="inlineStr"><is><t>Hal </t><t>2</t></is></c></row></sheetData></worksheet>');
    $zip->addFromString('xl/worksheets/sheet10.xml','<worksheet><sheetData><row><c r="A1"><v>WRONG</v></c></row></sheetData></worksheet>');$zip->close();
    $matrix=mp_sync_matrix(file_get_contents($file));check($matrix['matrix'][0]===['WCL NR.','ZAAKNAAM'],'headers');check($matrix['matrix'][1]===['WCL0001','Hal 2'],'shared and inline strings');check($matrix['redRows']===[1],'red styles');
    $node=trim(shell_exec('command -v node'));
    $result=mp_sync_worker(['node_path'=>$node],array_merge($matrix,['devices'=>[],'fileName'=>'fixture.xlsx','syncMoment'=>'2026-10-06T18:00','loggedAt'=>'2026-10-06T16:00:00Z']));
    check(count($result['devices'])===1 && $result['devices'][0]['status']==='Buiten dienst','worker');
    try{mp_sync_xml('<!DOCTYPE x [<!ENTITY ext SYSTEM "file:///etc/passwd">]><x>&ext;</x>');throw new RuntimeException('XXE accepted');}catch(RuntimeException $e){check($e->getMessage()!=='XXE accepted','XXE rejected');}
    $state=['app'=>'Machinepark','schema'=>1,'devices'=>[],'parts'=>[['id'=>'p','stock'=>7]],'maintenance'=>[['id'=>'m']],'breakdowns'=>[],'actions'=>[['id'=>'a']]];
    mp_write_state($state);
    mp_sync_locked(function()use($state){$state['devices']=[['id'=>'dev','assetCode'=>'WCL0001']];mp_sync_save_run($state,['id'=>'run','at'=>'2026-10-06T16:00:00Z','status'=>'success','message'=>'one','changes'=>[['code'=>'WCL0001','field'=>'location','oldValue'=>'A','newValue'=>'B']]]);});
    $saved=mp_sync_state();check($saved['parts']===$state['parts']&&$saved['maintenance']===$state['maintenance']&&$saved['actions']===$state['actions'],'unrelated stores preserved');check($saved['deviceSync']['history'][0]['id']==='run','history persisted atomically');check(count(glob(MP_BACKUP_DIR.'/*.json'))===1,'backup');
    // Without setup, scheduled tasks are safely disabled; they do not touch devices.
    check(mp_sync_run()['status']==='disabled','default disabled');
    check(mp_sync_state()===$saved,'disabled unchanged');
    $bad=[['WCL NR.','ZAAKNAAM'],['WCL0001','A'],['wcl0001','B']];
    try {mp_sync_worker(['node_path'=>$node],['matrix'=>$bad,'devices'=>[],'redRows'=>[]]);throw new RuntimeException('Duplicate accepted');}catch(RuntimeException $e){check(strpos($e->getMessage(),'Dubbele WCL')!==false,'duplicate rejected');}
    check(mp_sync_state()===$saved,'failed worker never writes');
    echo "sharepoint sync PHP checks passed\n";
} finally {
    foreach(glob($dir.'/backups/*') as $f)unlink($f);rmdir($dir.'/backups');foreach(glob($dir.'/*') as $f)if(is_file($f))unlink($f);rmdir($dir);
}
