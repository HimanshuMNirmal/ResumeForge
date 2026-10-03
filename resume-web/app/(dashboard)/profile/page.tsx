import type { Metadata } from "next";
import { ProfileForm } from "@/components/profile/ProfileForm";
import { ImportExportPanel } from "@/components/profile/ImportExportPanel";

export const metadata: Metadata = { title: "Profile" };

export default function ProfilePage() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">Profile</h1>
        <p className="mt-1 text-sm text-zinc-500">Everything here is the source material for tailored resumes.</p>
      </header>
      <ImportExportPanel />
      <ProfileForm />
    </div>
  );
}
