import { useState } from "react";
import { Play, Terminal } from "lucide-react";

interface Argument {
  name: string;
  placeholder: string;
  type: string;
}

interface ScriptPanelProps {
  title: string;
  description: string;
  scriptName: string;
  arguments: Argument[];
  accentColor: "blue" | "purple";
}

export function ScriptPanel({
  title,
  description,
  scriptName,
  arguments: args,
  accentColor,
}: ScriptPanelProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [isRunning, setIsRunning] = useState(false);

  const accentColors = {
    blue: {
      bg: "bg-blue-50",
      border: "border-blue-200",
      text: "text-blue-600",
      button: "bg-blue-600 hover:bg-blue-700",
      icon: "text-blue-500",
    },
    purple: {
      bg: "bg-purple-50",
      border: "border-purple-200",
      text: "text-purple-600",
      button: "bg-purple-600 hover:bg-purple-700",
      icon: "text-purple-500",
    },
  };

  const colors = accentColors[accentColor];

  const handleInputChange = (name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleRun = () => {
    setIsRunning(true);
    // Simulate script execution
    setTimeout(() => {
      console.log(`Running ${scriptName} with:`, formData);
      setIsRunning(false);
    }, 2000);
  };

  return (
    <div className={`bg-white rounded-lg border ${colors.border} overflow-hidden`}>
      <div className={`${colors.bg} px-6 py-4 border-b ${colors.border}`}>
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <Terminal className={`${colors.icon} mt-1`} size={20} />
            <div>
              <h2 className={`${colors.text}`}>{title}</h2>
              <p className="text-gray-600 text-sm mt-1">{description}</p>
              <code className="text-xs text-gray-500 mt-2 inline-block bg-white px-2 py-1 rounded">
                {scriptName}
              </code>
            </div>
          </div>
        </div>
      </div>

      <div className="px-6 py-5">
        <div className="flex items-end gap-4 flex-wrap">
          {args.map((arg) => (
            <div key={arg.name} className="flex-1 min-w-[200px]">
              <label className="block text-sm text-gray-700 mb-2">
                {arg.name.replace(/_/g, " ")}
              </label>
              <input
                type={arg.type}
                placeholder={arg.placeholder}
                value={formData[arg.name] || ""}
                onChange={(e) => handleInputChange(arg.name, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-0 focus:ring-blue-500 text-gray-900"
              />
            </div>
          ))}
          <button
            onClick={handleRun}
            disabled={isRunning}
            className={`${colors.button} text-white px-6 py-2 rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <Play size={16} />
            {isRunning ? "Running..." : "Run"}
          </button>
        </div>
      </div>
    </div>
  );
}
