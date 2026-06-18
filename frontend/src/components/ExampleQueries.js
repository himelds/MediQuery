const ROLE_EXAMPLES = {
  doctor: [
    "What are the symptoms of diabetes?",
    "What is the dosage for paracetamol?",
    "What are the ICU hand hygiene steps?",
  ],
  nurse: [
    "What are the symptoms of diabetes?",
    "What is the infection control protocol?",
    "What is the leave policy?",
  ],
  billing_executive: [
    "What is the ICD-10 code for NSTEMI?",
    "How to submit an insurance claim?",
    "What is the leave policy?",
  ],
  technician: [
    "Ventilator calibration schedule?",
    "Equipment maintenance procedures?",
    "What is the code of conduct?",
  ],
  admin: [
    "What are the symptoms of diabetes?",
    "What is the ICD-10 code for NSTEMI?",
    "What is the leave policy?",
  ],
};

export default function ExampleQueries({ role, onSelect }) {
  const examples = ROLE_EXAMPLES[role] || ROLE_EXAMPLES.admin;

  return (
    <div className="space-y-2">
      <p className="text-sm text-gray-500">Try asking:</p>
      <div className="flex flex-wrap gap-2">
        {examples.map((q) => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            className="text-sm px-3 py-1.5 bg-white border border-gray-200 rounded-full hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
