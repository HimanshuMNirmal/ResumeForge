import type { Metadata } from "next";
import { KeyManager } from "@/components/keys/KeyManager";

export const metadata: Metadata = { title: "API keys" };

export default function KeysPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">API keys</h1>
      <KeyManager />
    </div>
  );
}
