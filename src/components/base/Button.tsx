
interface ButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  disabled?: boolean;
  className?: string;
}

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  onClick,
  type = 'button',
  disabled = false,
  className = '',
}: ButtonProps) {
  const baseClasses = 'font-semibold rounded-lg transition-all duration-200 cursor-pointer whitespace-nowrap flex items-center justify-center';
  
  const variantClasses = {
    primary: 'bg-orange-500 hover:bg-orange-600 text-white shadow-lg hover:shadow-xl',
    secondary: 'bg-black hover:bg-gray-800 text-white shadow-lg hover:shadow-xl',
    outline: 'border-2 border-orange-500 text-orange-500 hover:bg-orange-500 hover:text-white',
  };
  
  const sizeClasses = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg',
  };
  
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
    >
      {children}
    </button>
  );
}
