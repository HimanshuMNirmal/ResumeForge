import type { Metadata } from "next";
import { HistoryList } from "@/components/builder/HistoryList";

export const metadata: Metadata = { title: "History" };

export default function HistoryPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">History</h1>
      <HistoryList />
    </div>
  );
}
