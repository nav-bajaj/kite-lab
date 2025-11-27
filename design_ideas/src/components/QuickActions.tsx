import { 
  LogIn, 
  RefreshCw, 
  Download, 
  FolderOpen, 
  BarChart3, 
  FileText, 
  Settings,
  TrendingUp
} from "lucide-react";

export function QuickActions() {
  const quickLinks = [
    { icon: BarChart3, label: "Market Overview", color: "text-blue-600" },
    { icon: TrendingUp, label: "Portfolio", color: "text-purple-600" },
    { icon: FileText, label: "Reports", color: "text-blue-600" },
    { icon: Settings, label: "Settings", color: "text-purple-600" },
  ];

  const actionButtons = [
    { icon: LogIn, label: "Login Flow", color: "bg-blue-600 hover:bg-blue-700" },
    { icon: RefreshCw, label: "Refresh", color: "bg-purple-600 hover:bg-purple-700" },
    { icon: Download, label: "Update", color: "bg-blue-600 hover:bg-blue-700" },
    { icon: FolderOpen, label: "File Explorer", color: "bg-purple-600 hover:bg-purple-700" },
  ];

  return (
    <div className="bg-white border-t border-gray-200 mt-12">
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Quick Links */}
          <div>
            <h3 className="text-gray-900 mb-4">Quick Links</h3>
            <div className="grid grid-cols-2 gap-3">
              {quickLinks.map((link) => (
                <button
                  key={link.label}
                  className="flex items-center gap-3 px-4 py-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors text-left"
                >
                  <link.icon className={link.color} size={20} />
                  <span className="text-gray-700">{link.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div>
            <h3 className="text-gray-900 mb-4">Actions</h3>
            <div className="grid grid-cols-2 gap-3">
              {actionButtons.map((button) => (
                <button
                  key={button.label}
                  className={`flex items-center justify-center gap-2 px-4 py-3 ${button.color} text-white rounded-lg transition-colors`}
                >
                  <button.icon size={20} />
                  <span>{button.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
