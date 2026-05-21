/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    fontFamily: {
      // 2026-05 Reset: 删除 ui-design skill FORBIDDEN FONTS:
      //   ❌ Inter / Roboto / Arial / Helvetica / Helvetica Neue / system-ui / -apple-system
      // 中文优先字体栈（PingFang/YaHei/Noto Sans SC 均为系统/Web 字体）。
      // 英文/数字用 generic sans-serif 兜底，由浏览器选系统默认（不强制具体字体名）。
      sans: [
        "PingFang SC",
        "Microsoft YaHei",
        "Hiragino Sans GB",
        "Noto Sans SC",
        "WenQuanYi Micro Hei",
        "sans-serif",
      ],
      // 衬线（Editorial Luxury 核心字体）— 用于 Display / H1 / 业务域名 / 法条引用
      serif: [
        "Noto Serif SC",
        "Source Han Serif SC",
        "Songti SC",
        "STSong",
        "SimSun",
        "serif",
      ],
      // 等宽（合同 diff / 代码片段 / 数字对齐）
      mono: [
        "JetBrains Mono",
        "SF Mono",
        "Menlo",
        "Monaco",
        "Consolas",
        "Liberation Mono",
        "Courier New",
        "monospace",
      ],
    },
    extend: {
      width: {
        '4.5': '1.125rem',
      },
      height: {
        '4.5': '1.125rem',
      },
      colors: {
        border: {
          DEFAULT: "hsl(var(--border))",
          strong: "hsl(var(--border-strong))",
          subtle: "hsl(var(--border-subtle))",
        },
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: {
          DEFAULT: "hsl(var(--foreground))",
          tertiary: "hsl(var(--text-tertiary))",
          disabled: "hsl(var(--text-disabled))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
          50: "hsl(var(--primary-50))",
          100: "hsl(var(--primary-100))",
          200: "hsl(var(--primary-200))",
          300: "hsl(var(--primary-300))",
          400: "hsl(var(--primary-400))",
          500: "hsl(var(--primary-500))",
          600: "hsl(var(--primary-600))",
          700: "hsl(var(--primary-700))",
          800: "hsl(var(--primary-800))",
          900: "hsl(var(--primary-900))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        surface: {
          1: "hsl(var(--surface-1))",
          2: "hsl(var(--surface-2))",
          3: "hsl(var(--surface-3))",
        },
        // 语义状态色
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        info: {
          DEFAULT: "hsl(var(--info))",
          foreground: "hsl(var(--info-foreground))",
        },
        // AI 语义色
        ai: {
          DEFAULT: "hsl(var(--ai))",
          foreground: "hsl(var(--ai-foreground))",
          surface: "hsl(var(--ai-surface))",
          thinking: "hsl(var(--ai-thinking))",
          "thinking-surface": "hsl(var(--ai-thinking-surface))",
          suggestion: "hsl(var(--ai-suggestion))",
          "suggestion-surface": "hsl(var(--ai-suggestion-surface))",
          citation: "hsl(var(--ai-citation))",
          "citation-surface": "hsl(var(--ai-citation-surface))",
        },
        confidence: {
          high: "hsl(var(--ai-confidence-high))",
          medium: "hsl(var(--ai-confidence-medium))",
          low: "hsl(var(--ai-confidence-low))",
        },
        risk: {
          high: "hsl(var(--risk-high))",
          "high-surface": "hsl(var(--risk-high-surface))",
          medium: "hsl(var(--risk-medium))",
          "medium-surface": "hsl(var(--risk-medium-surface))",
          low: "hsl(var(--risk-low))",
          "low-surface": "hsl(var(--risk-low-surface))",
        },
        // 图谱节点语义色
        node: {
          law: "hsl(var(--node-law))",
          case: "hsl(var(--node-case))",
          party: "hsl(var(--node-party))",
          organization: "hsl(var(--node-organization))",
          lawyer: "hsl(var(--node-lawyer))",
          query: "hsl(var(--node-query))",
          conclusion: "hsl(var(--node-conclusion))",
          other: "hsl(var(--node-other))",
        },
        // 2026-05 Reset：删除 16 个 colors.domain.* utility
        // 业务域可视化改用 序号 + 衬线域名 + 字距层次（不用色）
        // 详见 docs/design/v3-prototype-editorial.html
      },
      // 排版系统 (DesignDNA §3 — 字距随字号反向缩放)
      fontSize: {
        "display":  ["2.5rem",   { lineHeight: "1.2",  letterSpacing: "-0.03em", fontWeight: "500" }],
        "h1":       ["2rem",     { lineHeight: "1.25", letterSpacing: "-0.02em", fontWeight: "500" }],
        "h2":       ["1.5rem",   { lineHeight: "1.3",  letterSpacing: "-0.015em",fontWeight: "500" }],
        "h3":       ["1.25rem",  { lineHeight: "1.35", letterSpacing: "-0.01em", fontWeight: "500" }],
        "body-lg":  ["1rem",     { lineHeight: "1.75", letterSpacing: "0",       fontWeight: "400" }],
        "body":     ["0.875rem", { lineHeight: "1.65", letterSpacing: "0",       fontWeight: "400" }],
        "body-sm":  ["0.8125rem",{ lineHeight: "1.6",  letterSpacing: "0.005em", fontWeight: "400" }],
        "caption":  ["0.75rem",  { lineHeight: "1.5",  letterSpacing: "0.01em",  fontWeight: "400" }],
        "micro":    ["0.6875rem",{ lineHeight: "1.4",  letterSpacing: "0.02em",  fontWeight: "500" }],
      },
      // 动效
      transitionDuration: {
        "instant": "var(--duration-instant)",
        "fast": "var(--duration-fast)",
        "normal": "var(--duration-normal)",
        "slow": "var(--duration-slow)",
      },
      transitionTimingFunction: {
        "standard": "var(--ease-standard)",
        "decelerate": "var(--ease-decelerate)",
        "spring": "var(--ease-spring)",
      },
      borderRadius: {
        // Shadcn 兼容（保留）
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        // DesignDNA 8 级圆角尺度
        none: "var(--radius-none)",
        micro: "var(--radius-micro)",
        subtle: "var(--radius-subtle)",
        dd: "var(--radius-md)",      // designdna 标准 8px
        dd_lg: "var(--radius-lg)",   // 12px
        dd_xl: "var(--radius-xl)",   // 16px
        dd_2xl: "var(--radius-2xl)", // 20px
        pill: "var(--radius-pill)",
      },
      zIndex: {
        base: "var(--z-base)",
        dropdown: "var(--z-dropdown)",
        sticky: "var(--z-sticky)",
        drawer: "var(--z-drawer)",
        overlay: "var(--z-overlay)",
        modal: "var(--z-modal)",
        popover: "var(--z-popover)",
        toast: "var(--z-toast)",
        tooltip: "var(--z-tooltip)",
      },
      letterSpacing: {
        // DESIGN.md 字距系统
        "heading-xl": "-0.03em",   // Display Hero / large hero text
        "heading-lg": "-0.02em",   // Page Title
        "heading-md": "-0.01em",   // Section / Panel Title
        "caption": "0.01em",       // Caption / timestamp
      },
      boxShadow: {
        // 兼容旧值
        card: "var(--shadow-card)",
        float: "var(--shadow-float)",
        // DesignDNA 5 级多层阴影
        "elev-0": "var(--shadow-0)",
        "elev-1": "var(--shadow-1)",
        "elev-2": "var(--shadow-2)",
        "elev-3": "var(--shadow-3)",
        "elev-4": "var(--shadow-4)",
        "elev-5": "var(--shadow-5)",
        "focus-ring": "var(--shadow-focus)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
        "bounce-subtle": {
          "0%, 100%": { transform: "scale(1)" },
          "50%": { transform: "scale(1.15)" },
        },
        "ai-pulse": {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
        "ai-cursor": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
        "ai-thinking-dot": {
          "0%, 80%, 100%": { transform: "scale(0.6)", opacity: "0.4" },
          "40%": { transform: "scale(1)", opacity: "1" },
        },
        "suggestion-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "risk-shake": {
          "0%, 100%": { transform: "translateX(0)" },
          "20%": { transform: "translateX(-3px)" },
          "40%": { transform: "translateX(3px)" },
          "60%": { transform: "translateX(-2px)" },
          "80%": { transform: "translateX(2px)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "bounce-subtle": "bounce-subtle 2s ease-in-out infinite",
        "ai-pulse": "ai-pulse 1.5s ease-in-out infinite",
        "ai-cursor": "ai-cursor 1s ease-in-out infinite",
        "ai-thinking-dot": "ai-thinking-dot 1.4s ease-in-out infinite",
        "suggestion-in": "suggestion-in 250ms cubic-bezier(0.2, 0, 0, 1)",
        "risk-shake": "risk-shake 400ms cubic-bezier(0.2, 0, 0, 1)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
