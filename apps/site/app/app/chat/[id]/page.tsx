export const instant = false;

import Detail from "./detail";

export default async function ChatThreadPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <Detail threadId={id} />;
}
