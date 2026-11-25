import { Inter } from "next/font/google";
import FeedScreen from "@/components/feed/FeedScreen";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export default function FeedPage() {
  return (
    <div className={`feed-v2 ${inter.className}`}>
      <FeedScreen />
    </div>
  );
}
