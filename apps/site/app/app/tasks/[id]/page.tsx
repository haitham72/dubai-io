export const instant = false;

import Detail from "./detail";

export default async function TaskPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <Detail id={id} />;
}
