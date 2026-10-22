export const instant = false;

import Detail from "./detail";

export default async function PostPage({
  params,
}: {
  params: Promise<{ postId: string }>;
}) {
  const { postId } = await params;
  return <Detail postId={postId} />;
}
