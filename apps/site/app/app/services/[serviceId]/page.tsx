export const instant = false;

import Detail from "./detail";

export default async function ServicePage({
  params,
}: {
  params: Promise<{ serviceId: string }>;
}) {
  const { serviceId } = await params;
  return <Detail serviceId={serviceId} />;
}
