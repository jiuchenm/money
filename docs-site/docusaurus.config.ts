import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const config: Config = {
  title: '潮 Tide',
  tagline: '潮有涨落，be water——看清周期在哪一段，该进则进，该退则退',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://tide.local',
  baseUrl: '/',

  onBrokenLinks: 'warn',

  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'zh-Hans',
    locales: ['zh-Hans'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: '/', // 文档直接挂在根路径，无 /kb 层
        },
        blog: {
          showReadingTime: true,
          routeBasePath: 'blog',
          blogTitle: '分析日志',
          blogDescription: '定期分析日志——雷达站的心跳',
          postsPerPage: 10,
          blogSidebarTitle: '全部分析',
          blogSidebarCount: 'ALL',
          onInlineTags: 'warn',
          onInlineAuthors: 'warn',
          onUntruncatedBlogPosts: 'ignore',
        },
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themes: ['@docusaurus/theme-mermaid'],

  themeConfig: {
    colorMode: {
      defaultMode: 'dark',
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: '潮 Tide',
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'kbSidebar',
          position: 'left',
          label: '知识库',
        },
        {to: '/industry', label: '产业研究', position: 'left'},
        {to: '/track', label: 'Track', position: 'left'},
        {to: '/build', label: '品牌实践', position: 'left'},
        {to: '/blog', label: '分析日志', position: 'left'},
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: '透镜',
          items: [
            {label: '浪潮识别方法论', to: '/framework/taxonomy'},
            {label: '标的甄别', to: '/selection/capability'},
            {label: '人形机器人产业研究', to: '/industry/robotics'},
            {label: '高端黄金珠宝研究', to: '/industry/gold-jewelry'},
            {label: 'AI 办公产业研究', to: '/industry/ai-office'},
          ],
        },
        {
          title: '雷达站',
          items: [
            {label: '全球黄金周期 Track', to: '/track/gold'},
            {label: '老铺黄金 Track', to: '/track/laopu-gold'},
            {label: '活跃浪潮档案', to: '/waves/template'},
            {label: '分析日志', to: '/blog'},
          ],
        },
        {
          title: '实践',
          items: [
            {label: '从零做咖啡器具品牌', to: '/build/coffee-gear'},
            {label: '品牌案例', to: '/build/coffee-gear/brand-cases'},
            {label: '供应商与打样', to: '/build/coffee-gear/suppliers'},
          ],
        },
        {
          title: '参考',
          items: [
            {label: '数据源', to: '/reference/data-sources'},
          ],
        },
      ],
      copyright: `潮 Tide · 看清周期，be water · 开源投资知识库`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
