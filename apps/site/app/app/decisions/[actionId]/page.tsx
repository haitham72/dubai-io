export const instant = false;

import Detail from "./detail";

export default async function DecisionPage({
  params,
}: {
  params: Promise<{ actionId: string }>;
}) {
  const { actionId } = await params;
  return <Detail actionId={actionId} />;
}
