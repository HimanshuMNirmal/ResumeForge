import { Suspense } from "react";
import type { Metadata } from "next";
import { ResumeStudio } from "@/components/builder/ResumeStudio";

export const metadata: Metadata = { title: "Resume builder" };

export default function BuilderPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Resume builder</h1>
      <Suspense fallback={null}><ResumeStudio /></Suspense>
    </div>
  );
}
