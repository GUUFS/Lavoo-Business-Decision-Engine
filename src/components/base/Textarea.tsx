interface TextareaProps {
  label?: string;
  placeholder?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  required?: boolean;
  rows?: number;
  className?: string;
  name?: string;
  maxLength?: number;
}

export default function Textarea({
  label,
  placeholder,
  value,
  onChange,
  required = false,
  rows = 4,
  className = '',
  name,
  maxLength = 500,
}: TextareaProps) {
  return (
    <div className={`w-full ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label}
          {required && <span className="text-orange-500 ml-1">*</span>}
        </label>
      )}
      <textarea
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        rows={rows}
        maxLength={maxLength}
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors text-sm resize-vertical"
      />
      {maxLength && (
        <div className="text-xs text-gray-500 mt-1 text-right">
          {value?.length || 0}/{maxLength}
        </div>
      )}
    </div>
  );
}