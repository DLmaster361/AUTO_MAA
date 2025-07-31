export type ThemeMode = 'system' | 'light' | 'dark';

export class ThemeManager {
    private static instance: ThemeManager;
    private currentTheme: ThemeMode = 'system';
    private listeners: ((theme: ThemeMode, isDark: boolean) => void)[] = [];

    private constructor() {
        this.init();
    }

    static getInstance(): ThemeManager {
        if (!ThemeManager.instance) {
            ThemeManager.instance = new ThemeManager();
        }
        return ThemeManager.instance;
    }

    private init() {
        // 从 localStorage 读取保存的主题设置
        const savedTheme = localStorage.getItem('theme-mode') as ThemeMode;
        if (savedTheme && ['system', 'light', 'dark'].includes(savedTheme)) {
            this.currentTheme = savedTheme;
        }

        // 监听系统主题变化
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', () => {
            if (this.currentTheme === 'system') {
                this.applyTheme();
            }
        });

        // 应用初始主题
        this.applyTheme();
    }

    private applyTheme() {
        const isDark = this.getIsDark();
        const themeValue = isDark ? 'dark' : 'light';

        document.documentElement.setAttribute('data-theme', themeValue);

        // 通知所有监听器
        this.listeners.forEach(listener => {
            listener(this.currentTheme, isDark);
        });
    }

    private getIsDark(): boolean {
        switch (this.currentTheme) {
            case 'dark':
                return true;
            case 'light':
                return false;
            case 'system':
            default:
                return window.matchMedia('(prefers-color-scheme: dark)').matches;
        }
    }

    setTheme(theme: ThemeMode) {
        this.currentTheme = theme;
        localStorage.setItem('theme-mode', theme);
        this.applyTheme();
    }

    getTheme(): ThemeMode {
        return this.currentTheme;
    }

    getIsDarkMode(): boolean {
        return this.getIsDark();
    }

    addListener(listener: (theme: ThemeMode, isDark: boolean) => void) {
        this.listeners.push(listener);
        // 立即调用一次，传递当前状态
        listener(this.currentTheme, this.getIsDark());
    }

    removeListener(listener: (theme: ThemeMode, isDark: boolean) => void) {
        const index = this.listeners.indexOf(listener);
        if (index > -1) {
            this.listeners.splice(index, 1);
        }
    }
}

export const themeManager = ThemeManager.getInstance();