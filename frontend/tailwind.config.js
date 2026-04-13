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
      sans: [
        "Inter",
        "PingFang SC",
        "Microsoft YaHei",
        "Hiragino Sans GB",
        "WenQuanYi Micro Hei",
        "Helvetica Neue",
        "Arial",
        "sans-serif",
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
      },
      // 排版系统
      fontSize: {
        "display": ["2.5rem", { lineHeight: "1.2", fontWeight: "500" }],
        "h1": ["2rem", { lineHeight: "1.25", fontWeight: "500" }],
        "h2": ["1.5rem", { lineHeight: "1.3", fontWeight: "500" }],
        "h3": ["1.25rem", { lineHeight: "1.35", fontWeight: "500" }],
        "body-lg": ["1rem", { lineHeight: "1.75", fontWeight: "400" }],
        "body": ["0.875rem", { lineHeight: "1.65", fontWeight: "400" }],
        "body-sm": ["0.8125rem", { lineHeight: "1.6", fontWeight: "400" }],
        "caption": ["0.75rem", { lineHeight: "1.5", fontWeight: "400" }],
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
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      letterSpacing: {
        // DESIGN.md 字距系统
        "heading-xl": "-0.03em",   // Display Hero / large hero text
        "heading-lg": "-0.02em",   // Page Title
        "heading-md": "-0.01em",   // Section / Panel Title
        "caption": "0.01em",       // Caption / timestamp
      },
      boxShadow: {
        card: "var(--shadow-card)",
        float: "var(--shadow-float)",
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
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "bounce-subtle": "bounce-subtle 2s ease-in-out infinite",
        "ai-pulse": "ai-pulse 1.5s ease-in-out infinite",
        "ai-cursor": "ai-cursor 1s ease-in-out infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
