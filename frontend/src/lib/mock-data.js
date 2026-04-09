export const mockSocData = {
  overview: {
    stats: {
      alerts: 3,
      cases: 2,
      campaigns: 2,
      playbooks: 2,
      messages: 3,
      assets: 3,
      critical_alerts: 1,
      running_playbooks: 1,
      open_cases: 2,
      mtta_minutes: 8,
      mttr_minutes: 42
    },
    metrics: {
      severity_distribution: [
        { name: "Critical", count: 1 },
        { name: "High", count: 1 },
        { name: "Medium", count: 1 }
      ],
      top_assets: [
        { name: "finance@company.local", count: 2 },
        { name: "host-win11-22", count: 1 }
      ],
      top_users: [
        { name: "finance@company.local", count: 2 },
        { name: "hr-laptop-04", count: 1 }
      ],
      agent_status: [
        { name: "Online", count: 2 },
        { name: "Attention", count: 1 },
        { name: "Contained", count: 0 }
      ]
    },
    recent_activity: [
      {
        rowid: "msg-1",
        role: "SystemMessage",
        content: "Case created from correlated phishing alerts in local-dev mode.",
        ts: "2026-04-08T09:18:30Z"
      },
      {
        rowid: "msg-2",
        role: "AIMessage",
        content: "Assessed likely phishing. Recommended user isolation from credential prompts and sender-domain block review.",
        ts: "2026-04-08T09:19:20Z"
      },
      {
        rowid: "msg-3",
        role: "ToolMessage",
        content: "Knowledge search completed. Similar incidents found in finance mailbox over previous 30 days.",
        ts: "2026-04-08T09:19:54Z"
      }
    ]
  },
  alerts: [
    {
      rowid: "3fd9fcdb-ac20-48fa-894b-32a71de8bf0b",
      title: "User-reported phishing email",
      severity: "High",
      rule_id: "ES-Rule-21-Phishing-User-Report-Mail",
      target: "finance@company.local",
      product_name: "Email Security",
      status: "New",
      first_seen_time: "2026-04-08T09:14:00Z",
      summary: "Email contains credential-harvesting language and suspicious domain indicators.",
      sender_domain: "secure-login-update-required.com",
      threat_analysis: {
        mitre_attack: [
          { tactic: "Initial Access", technique: "Phishing", id: "T1566" }
        ],
        risk_score: 78,
        confidence_score: 0.82,
        explanation: "Language and domain indicators align with a phishing lure targeting finance users."
      }
    },
    {
      rowid: "7f3a2a10-d0e0-42c5-b3a1-e212fc9f2231",
      title: "Suspect C2 communication",
      severity: "Critical",
      rule_id: "NDR-Rule-05-Suspect-C2-Communication",
      target: "host-win11-22",
      product_name: "Network Sensor",
      status: "New",
      first_seen_time: "2026-04-08T08:40:00Z",
      summary: "Outbound beaconing pattern detected to low-reputation infrastructure."
    },
    {
      rowid: "5f94cb6a-49fa-43e4-b2bb-6df838758e99",
      title: "Suspicious process spawned by Office",
      severity: "Medium",
      rule_id: "EDR-Rule-11-Suspicious-Process-Spawned-by-Office",
      target: "hr-laptop-04",
      product_name: "EDR Agent",
      status: "In Progress",
      first_seen_time: "2026-04-08T07:55:00Z",
      summary: "Office process lineage indicates macro-assisted child process execution."
    }
  ],
  campaigns: [
    {
      rowid: "campaign-finance-phish-2026-04-08-h08",
      name: "Campaign around finance@company.local",
      correlation_basis: "user:finance@company.local|asset:-|network:secure-login-update-required.com",
      window: "2026-04-08-h08",
      alert_count: 2,
      users: ["finance@company.local"],
      assets: ["fin-ws-01"],
      domains: ["secure-login-update-required.com"],
      ips: [],
      attack_summary: ["T1566 Phishing"],
      risk_score: 78,
      latest_seen: "2026-04-08T09:14:00Z",
      alerts: [
        {
          rowid: "3fd9fcdb-ac20-48fa-894b-32a71de8bf0b",
          title: "User-reported phishing email",
          severity: "High",
          rule_id: "ES-Rule-21-Phishing-User-Report-Mail",
          first_seen_time: "2026-04-08T09:14:00Z"
        }
      ]
    },
    {
      rowid: "campaign-host-win11-22-2026-04-08-h08",
      name: "Campaign around host-win11-22",
      correlation_basis: "user:-|asset:host-win11-22|network:-",
      window: "2026-04-08-h08",
      alert_count: 1,
      users: [],
      assets: ["host-win11-22"],
      domains: [],
      ips: ["185.44.10.90"],
      attack_summary: ["T1071 Application Layer Protocol"],
      risk_score: 95,
      latest_seen: "2026-04-08T08:40:00Z",
      alerts: [
        {
          rowid: "7f3a2a10-d0e0-42c5-b3a1-e212fc9f2231",
          title: "Suspect C2 communication",
          severity: "Critical",
          rule_id: "NDR-Rule-05-Suspect-C2-Communication",
          first_seen_time: "2026-04-08T08:40:00Z"
        }
      ]
    }
  ],
  cases: [
    {
      rowid: "d361287d-60b5-413a-833f-a4927cfeedc7",
      title: "Phishing cluster affecting finance users",
      priority: "High",
      owner: "Local SOC Pipeline",
      status: "Triage",
      linked_alerts: 4,
      last_updated: "2026-04-08T09:21:00Z",
      playbook: "L3 SOC Analyst Agent With Tools",
      summary: "Local-dev grouped phishing alerts by recipient and day window.",
      assignment: { owner: "Local SOC Pipeline", assigned: false }
    },
    {
      rowid: "0d66f45c-e86e-41ff-b920-1d1d8040f6cd",
      title: "Potential malware beaconing from endpoint cluster",
      priority: "Critical",
      owner: "Local SOC Pipeline",
      status: "Investigating",
      linked_alerts: 2,
      last_updated: "2026-04-08T08:51:00Z",
      playbook: "L3 SOC Analyst Agent With Tools",
      summary: "Beaconing indicators under investigation with automation support.",
      assignment: { owner: "Local SOC Pipeline", assigned: false }
    }
  ],
  assets: [
    {
      rowid: "asset-fin-ws-01",
      hostname: "fin-ws-01",
      owner: "finance@company.local",
      criticality: "High",
      status: "Online",
      last_seen: "2026-04-08T09:22:00Z",
      operating_system: "Windows 11 Enterprise",
      ip_address: "10.10.20.11",
      software_count: 3,
      vulnerability_count: 1,
      integrity_findings_count: 1,
      software_inventory: [
        { name: "7-Zip", version: "22.01" },
        { name: "OpenSSL", version: "1.1.1k" },
        { name: "Microsoft Office", version: "2024.2401" }
      ],
      vulnerabilities: [
        { cve: "CVE-2026-12001", severity: "Critical", package: "OpenSSL", installed_version: "1.1.1k", fixed_in: "3.0.15" }
      ],
      integrity_findings: [
        { path: "C:\\ProgramData\\Startup\\invoice_updater.ps1", severity: "High" }
      ]
    },
    {
      rowid: "asset-edge-proxy-01",
      hostname: "edge-proxy-01",
      owner: "platform@company.local",
      criticality: "Critical",
      status: "Attention",
      last_seen: "2026-04-08T09:23:00Z",
      operating_system: "Ubuntu 22.04 LTS",
      ip_address: "10.10.10.5",
      software_count: 3,
      vulnerability_count: 1,
      integrity_findings_count: 1,
      software_inventory: [
        { name: "Nginx", version: "1.22.0" },
        { name: "OpenSSH", version: "8.9p1" },
        { name: "OpenSSL", version: "3.0.2" }
      ],
      vulnerabilities: [
        { cve: "CVE-2026-22014", severity: "High", package: "Nginx", installed_version: "1.22.0", fixed_in: "1.24.1" }
      ],
      integrity_findings: [
        { path: "/var/www/html/uploads/invoice-review.php", severity: "Critical" }
      ]
    },
    {
      rowid: "asset-db-core-01",
      hostname: "db-core-01",
      owner: "dba@company.local",
      criticality: "Critical",
      status: "Online",
      last_seen: "2026-04-08T09:20:00Z",
      operating_system: "Ubuntu 20.04 LTS",
      ip_address: "10.10.30.20",
      software_count: 3,
      vulnerability_count: 1,
      integrity_findings_count: 0,
      software_inventory: [
        { name: "PostgreSQL", version: "13.8" },
        { name: "glibc", version: "2.31" },
        { name: "OpenSSL", version: "1.1.1f" }
      ],
      vulnerabilities: [
        { cve: "CVE-2026-33177", severity: "High", package: "glibc", installed_version: "2.31", fixed_in: "2.39" }
      ],
      integrity_findings: []
    }
  ],
  playbooks: [
    {
      rowid: "8bdbcaad-396b-4a16-810f-11904f44f6e0",
      name: "L3 SOC Analyst Agent With Tools",
      status: "Success",
      started_at: "2026-04-08T09:18:00Z",
      finished_at: "2026-04-08T09:21:00Z",
      target_id: "d361287d-60b5-413a-833f-a4927cfeedc7",
      remark: "SOC analysis completed with potential tool-assisted enrichment."
    },
    {
      rowid: "6a20f7d5-718f-4c93-a6c6-9f2deba37cb9",
      name: "L3 SOC Analyst Agent With Tools",
      status: "Running",
      started_at: "2026-04-08T08:49:00Z",
      finished_at: null,
      target_id: "0d66f45c-e86e-41ff-b920-1d1d8040f6cd",
      remark: "Awaiting final case recommendation."
    }
  ],
  messages: [
    {
      rowid: "msg-1",
      role: "SystemMessage",
      content: "Case created from correlated phishing alerts in local-dev mode.",
      ts: "2026-04-08T09:18:30Z"
    },
    {
      rowid: "msg-2",
      role: "AIMessage",
      content: "Assessed likely phishing. Recommended user isolation from credential prompts and sender-domain block review.",
      ts: "2026-04-08T09:19:20Z"
    },
    {
      rowid: "msg-3",
      role: "ToolMessage",
      content: "Knowledge search completed. Similar incidents found in finance mailbox over previous 30 days.",
      ts: "2026-04-08T09:19:54Z"
    }
  ],
  audit: [
    {
      rowid: "audit-1",
      role: "AuditLog",
      action: "create_ticket",
      target_type: "case",
      target_rowid: "d361287d-60b5-413a-833f-a4927cfeedc7",
      status: "completed",
      content: "Local incident ticket created for analyst follow-up.",
      details: { summary: "Local incident ticket created for analyst follow-up." },
      ts: "2026-04-08T09:20:10Z"
    }
  ],
  responseJobs: [
    {
      rowid: "resp-1",
      action: "create_ticket",
      target_type: "case",
      target_rowid: "d361287d-60b5-413a-833f-a4927cfeedc7",
      status: "completed",
      started_at: "2026-04-08T09:20:07Z",
      finished_at: "2026-04-08T09:20:10Z",
      summary: "Created local incident ticket and linked it to the case.",
      outputs: {
        summary: "Created local incident ticket and linked it to the case.",
        linked_case: "d361287d-60b5-413a-833f-a4927cfeedc7"
      },
      role: "ResponseJob",
      ts: "2026-04-08T09:20:10Z"
    },
    {
      rowid: "resp-2",
      action: "assign",
      target_type: "alert",
      target_rowid: "3fd9fcdb-ac20-48fa-894b-32a71de8bf0b",
      status: "completed",
      started_at: "2026-04-08T09:18:50Z",
      finished_at: "2026-04-08T09:18:51Z",
      summary: "Assigned alert to Local SOC Analyst.",
      outputs: {
        summary: "Assigned alert to Local SOC Analyst.",
        linked_alert: "3fd9fcdb-ac20-48fa-894b-32a71de8bf0b"
      },
      role: "ResponseJob",
      ts: "2026-04-08T09:18:51Z"
    },
    {
      rowid: "resp-3",
      action: "run_playbook",
      target_type: "case",
      target_rowid: "0d66f45c-e86e-41ff-b920-1d1d8040f6cd",
      status: "completed",
      started_at: "2026-04-08T08:49:00Z",
      finished_at: "2026-04-08T08:49:02Z",
      summary: "Queued the default local-dev case playbook.",
      outputs: {
        summary: "Queued the default local-dev case playbook.",
        linked_case: "0d66f45c-e86e-41ff-b920-1d1d8040f6cd"
      },
      role: "ResponseJob",
      ts: "2026-04-08T08:49:02Z"
    }
  ]
};
