import { Inter } from "next/font/google";
import FeedScreen from "@/components/feed/FeedScreen";
import "@/styles/feed.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export default function FeedPage() {
  return (
    <div className={`feed-v2 ${inter.className}`}>
      <FeedScreen />
    </div>
  );
}
