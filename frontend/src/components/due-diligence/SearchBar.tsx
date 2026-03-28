import { useState } from 'react';
import { icons } from '@/lib/icons';
import { cardStyle, inputStyle, buttonStyle, iconSize, heading } from '@/lib/design-tokens';

interface SearchBarProps {
  onSearch: (companyName: string) => void;
  isSearching: boolean;
}

export function SearchBar({ onSearch, isSearching }: SearchBarProps) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isSearching) {
      onSearch(input.trim());
    }
  };

  const quickSearchExamples = [
    '科技有限公司',
    '贸易公司',
    '建筑集团',
  ];

  return (
    <div className={`${cardStyle.base} rounded-2xl p-6`}>
      <form onSubmit={handleSubmit} className="mb-4">
        <div className="relative">
          <icons.Search className={`absolute left-4 top-1/2 -translate-y-1/2 ${iconSize.md} text-muted-foreground`} />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入企业名称进行尽调查询..."
            disabled={isSearching}
            className={`${inputStyle.search} pl-12 pr-32 py-4 rounded-xl disabled:opacity-50`}
          />
          <button
            type="submit"
            disabled={!input.trim() || isSearching}
            className={`${buttonStyle.primary} absolute right-2 top-1/2 -translate-y-1/2 px-6 py-2.5 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm`}
          >
            {isSearching ? <icons.Loader2 className={`${iconSize.sm} animate-spin`} /> : <icons.Sparkles className={iconSize.sm} />}
            {isSearching ? '调查中...' : '开始调查'}
          </button>
        </div>
      </form>

      <div className="flex items-center gap-2">
        <span className={heading.micro}>快速开始：</span>
        {quickSearchExamples.map((example) => (
          <button
            key={example}
            onClick={() => {
              setInput(example);
              onSearch(example);
            }}
            disabled={isSearching}
            className={`${buttonStyle.ghost} rounded-full text-xs disabled:opacity-50`}
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}
