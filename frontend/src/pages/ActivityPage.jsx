import { ActivityFeed } from "../components/ActivityFeed";
import { SectionCard } from "../components/SectionCard";

export function ActivityPage({ messages, audit, responseJobs }) {
  const items = [...(messages || []), ...(audit || []), ...(responseJobs || [])].sort((a, b) => String(b.ts || "").localeCompare(String(a.ts || "")));
  return (
    <SectionCard
      title="Activity Timeline"
      subtitle="Structured analyst, agent, system, playbook, and response action activity grouped for readability."
    >
      <ActivityFeed items={items} />
    </SectionCard>
  );
}
