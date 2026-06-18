const ROLE_CONFIG = {
  doctor: { label: "Doctor", color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  nurse: { label: "Nurse", color: "bg-blue-50 text-blue-700 border-blue-200" },
  billing_executive: { label: "Billing", color: "bg-amber-50 text-amber-700 border-amber-200" },
  technician: { label: "Technician", color: "bg-purple-50 text-purple-700 border-purple-200" },
  admin: { label: "Admin", color: "bg-slate-100 text-slate-700 border-slate-300" },
};

export default function RoleBadge({ role }) {
  const config = ROLE_CONFIG[role] || { label: role, color: "bg-slate-50 text-slate-600 border-slate-200" };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium border ${config.color}`}>
      {config.label}
    </span>
  );
}
