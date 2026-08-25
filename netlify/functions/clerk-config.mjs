export default async () => {
  const publishableKey = process.env.CLERK_PUBLISHABLE_KEY;
  if (!publishableKey) {
    return Response.json(
      { error: 'CLERK_PUBLISHABLE_KEY is niet ingesteld in Netlify.' },
      { status: 500, headers: { 'cache-control': 'no-store' } }
    );
  }
  return Response.json(
    { publishableKey },
    { headers: { 'cache-control': 'no-store, max-age=0' } }
  );
};
