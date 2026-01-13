# Frontend Checklist — Aprender Sistema v2

> Checklist de qualidade para verificar antes de deploy em produção.
> Baseado em [Front-End Checklist](https://github.com/thedaviddias/Front-End-Checklist).

**Legenda de Prioridade:**
- 🔴 **Alta** — Obrigatório (quebra funcionalidade se ignorado)
- 🟡 **Média** — Recomendado (melhora qualidade)
- 🟢 **Baixa** — Opcional (nice to have)

---

## 📋 Head

### Meta Tags

- [ ] 🔴 **Charset UTF-8**: `<meta charset="UTF-8">`
- [ ] 🔴 **Viewport responsivo**: `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
- [ ] 🟡 **Title único por página**: Máximo 60 caracteres, descritivo
- [ ] 🟡 **Meta description**: Máximo 160 caracteres por página
- [ ] 🟢 **Theme color**: `<meta name="theme-color" content="#1890ff">`

### Favicon

- [ ] 🔴 **Favicon básico**: `/favicon.ico` (32x32)
- [ ] 🟡 **Apple Touch Icon**: `/apple-touch-icon.png` (180x180)
- [ ] 🟢 **Manifest.json**: Para PWA com ícones em múltiplos tamanhos

### Open Graph (Compartilhamento)

- [ ] 🟢 **og:title**: Título para redes sociais
- [ ] 🟢 **og:description**: Descrição para compartilhamento
- [ ] 🟢 **og:image**: Imagem de preview (1200x630)
- [ ] 🟢 **og:url**: URL canônica

---

## 📄 HTML

### Semântica

- [ ] 🔴 **HTML5 doctype**: `<!DOCTYPE html>`
- [ ] 🔴 **Lang attribute**: `<html lang="pt-BR">`
- [ ] 🟡 **Estrutura semântica**: `<header>`, `<main>`, `<footer>`, `<nav>`, `<section>`
- [ ] 🟡 **Headings hierárquicos**: H1 único por página, H2-H6 em ordem

### Validação

- [ ] 🟡 **W3C válido**: Sem erros críticos no [validator.w3.org](https://validator.w3.org/)
- [ ] 🔴 **Sem console errors**: Zero erros JavaScript no console
- [ ] 🔴 **Links funcionais**: Nenhum link quebrado (404)

### Páginas de Erro

- [ ] 🔴 **404 customizada**: Página de "não encontrado" amigável
- [ ] 🟡 **500 customizada**: Página de erro do servidor
- [ ] 🟡 **Offline page**: Para PWA (service worker)

---

## 🔤 Fontes

### Performance

- [ ] 🔴 **WOFF2 format**: Formato mais comprimido
- [ ] 🟡 **Font-display**: `font-display: swap` para evitar FOIT
- [ ] 🟡 **Preload fonts críticas**: `<link rel="preload" as="font">`
- [ ] 🟢 **Subset fonts**: Apenas caracteres necessários (latin)

### Fallbacks

- [ ] 🔴 **System font stack**: Fallback para fontes do sistema
- [ ] 🟡 **Font loading API**: Detectar quando fonte carregou

---

## 🎨 CSS / Tailwind

### Responsividade

- [ ] 🔴 **Mobile-first**: Breakpoints Tailwind (sm, md, lg, xl, 2xl)
- [ ] 🔴 **Testado em dispositivos**: iPhone SE, iPad, Desktop
- [ ] 🟡 **Orientação**: Funciona em portrait e landscape
- [ ] 🟡 **Touch targets**: Mínimo 44x44px para botões/links

### Performance

- [ ] 🔴 **PurgeCSS ativo**: Remover CSS não utilizado (Vite faz automaticamente)
- [ ] 🔴 **CSS minificado**: Build de produção
- [ ] 🟡 **Critical CSS**: Inline CSS above-the-fold
- [ ] 🟢 **CSS-in-JS mínimo**: Preferir Tailwind classes

### Compatibilidade

- [ ] 🔴 **Autoprefixer**: Vendor prefixes automáticos
- [ ] 🟡 **Browsers suportados**: Chrome 90+, Firefox 90+, Safari 14+, Edge 90+
- [ ] 🟢 **Print styles**: `@media print` se necessário

### Ant Design

- [ ] 🔴 **Theme customizado**: Cores do AS v2 configuradas
- [ ] 🟡 **Tree-shaking**: Import apenas componentes usados
- [ ] 🟡 **ConfigProvider**: Locale pt_BR configurado

---

## 🖼️ Imagens

### Otimização

- [ ] 🔴 **Imagens comprimidas**: WebP ou AVIF quando possível
- [ ] 🔴 **Dimensões corretas**: Não escalar imagens grandes via CSS
- [ ] 🟡 **Lazy loading**: `loading="lazy"` para imagens abaixo do fold
- [ ] 🟡 **Width/Height definidos**: Evitar layout shift (CLS)

### Formatos

- [ ] 🟡 **WebP com fallback**: `<picture>` com PNG/JPG fallback
- [ ] 🟢 **SVG para ícones**: Vetorial, escalável, pequeno
- [ ] 🟢 **Sprites SVG**: Agrupar ícones frequentes

### Responsivas

- [ ] 🟡 **srcset**: Múltiplas resoluções para diferentes telas
- [ ] 🟢 **Art direction**: Imagens diferentes por breakpoint

---

## ⚡ JavaScript / React

### Build

- [ ] 🔴 **Minificado**: Build de produção (Vite)
- [ ] 🔴 **Tree-shaking**: Remover código não utilizado
- [ ] 🔴 **Code splitting**: Lazy load de rotas (`React.lazy`)
- [ ] 🟡 **Bundle analysis**: Verificar tamanho com `vite-bundle-visualizer`

### Performance

- [ ] 🔴 **Sem memory leaks**: useEffect cleanup correto
- [ ] 🔴 **Keys em listas**: `key` único em `.map()`
- [ ] 🟡 **Memoização**: `useMemo`, `useCallback` onde necessário
- [ ] 🟡 **Virtualization**: Para listas longas (react-window)

### Qualidade

- [ ] 🔴 **ESLint sem erros**: Zero warnings críticos
- [ ] 🔴 **TypeScript strict**: Sem `any` implícito
- [ ] 🟡 **React DevTools**: Sem warnings em dev
- [ ] 🟢 **Error boundaries**: Capturar erros de componentes

### Segurança

- [ ] 🔴 **Sem `dangerouslySetInnerHTML`**: Ou sanitizar input
- [ ] 🔴 **Secrets no .env**: Nunca no código fonte
- [ ] 🟡 **Dependências atualizadas**: `npm audit` sem vulnerabilidades críticas

---

## 🔒 Segurança

### HTTPS

- [ ] 🔴 **HTTPS obrigatório**: Redirect HTTP → HTTPS
- [ ] 🔴 **Certificado válido**: Let's Encrypt ou similar
- [ ] 🟡 **HSTS header**: `Strict-Transport-Security`

### Headers de Segurança

- [ ] 🔴 **X-Content-Type-Options**: `nosniff`
- [ ] 🔴 **X-Frame-Options**: `DENY` ou `SAMEORIGIN`
- [ ] 🟡 **Content-Security-Policy**: Restringir sources
- [ ] 🟡 **X-XSS-Protection**: `1; mode=block`
- [ ] 🟢 **Referrer-Policy**: `strict-origin-when-cross-origin`

### Autenticação

- [ ] 🔴 **Tokens seguros**: HttpOnly cookies ou secure storage
- [ ] 🔴 **CSRF protection**: Token em requests mutáveis
- [ ] 🔴 **Session timeout**: Expiração automática
- [ ] 🟡 **Rate limiting**: Proteção contra brute force

### Dados Sensíveis

- [ ] 🔴 **Sem dados sensíveis no localStorage**: Usar sessionStorage ou cookies HttpOnly
- [ ] 🔴 **Sanitização de input**: Escapar HTML/SQL
- [ ] 🟡 **Mascarar dados**: CPF, telefone parcialmente ocultos

---

## 🚀 Performance

### Core Web Vitals

- [ ] 🔴 **LCP < 2.5s**: Largest Contentful Paint
- [ ] 🔴 **FID < 100ms**: First Input Delay
- [ ] 🔴 **CLS < 0.1**: Cumulative Layout Shift
- [ ] 🟡 **FCP < 1.8s**: First Contentful Paint
- [ ] 🟡 **TTFB < 600ms**: Time to First Byte

### Lighthouse Score (Mínimo)

- [ ] 🔴 **Performance**: ≥ 70
- [ ] 🔴 **Accessibility**: ≥ 90
- [ ] 🟡 **Best Practices**: ≥ 90
- [ ] 🟡 **SEO**: ≥ 90

### Otimizações

- [ ] 🔴 **Gzip/Brotli**: Compressão de assets
- [ ] 🔴 **Cache headers**: Assets estáticos com cache longo
- [ ] 🟡 **Preconnect**: `<link rel="preconnect">` para APIs
- [ ] 🟡 **Prefetch**: Rotas prováveis de navegação
- [ ] 🟢 **Service Worker**: Cache offline (PWA)

### Bundle Size

- [ ] 🔴 **JS inicial < 200KB**: Gzipped
- [ ] 🟡 **CSS < 50KB**: Gzipped
- [ ] 🟡 **Imagens otimizadas**: Total < 500KB na home

---

## ♿ Acessibilidade (WCAG 2.1)

### Navegação

- [ ] 🔴 **Keyboard navigation**: Tab order lógico
- [ ] 🔴 **Focus visible**: Outline visível ao navegar com teclado
- [ ] 🔴 **Skip links**: "Pular para conteúdo principal"
- [ ] 🟡 **Focus trap**: Em modais e dropdowns

### Semântica

- [ ] 🔴 **Alt text**: Todas imagens com `alt` descritivo
- [ ] 🔴 **Labels em forms**: `<label>` associado a inputs
- [ ] 🔴 **ARIA quando necessário**: `aria-label`, `aria-describedby`
- [ ] 🟡 **Landmarks**: `<main>`, `<nav>`, `<aside>`
- [ ] 🟡 **Live regions**: `aria-live` para conteúdo dinâmico

### Visual

- [ ] 🔴 **Contraste mínimo 4.5:1**: Texto normal
- [ ] 🔴 **Contraste mínimo 3:1**: Texto grande (18px+)
- [ ] 🟡 **Não depender só de cor**: Ícones ou texto adicional
- [ ] 🟡 **Zoom 200%**: Layout funcional com zoom
- [ ] 🟢 **Reduced motion**: Respeitar `prefers-reduced-motion`

### Formulários

- [ ] 🔴 **Mensagens de erro claras**: Texto descritivo, não só cor
- [ ] 🔴 **Required indicators**: Campos obrigatórios marcados
- [ ] 🟡 **Autocomplete**: Atributos corretos (`autocomplete="email"`)
- [ ] 🟡 **Input types corretos**: `type="email"`, `type="tel"`

### Testes

- [ ] 🔴 **Screen reader**: Testado com NVDA ou VoiceOver
- [ ] 🟡 **axe DevTools**: Sem erros críticos
- [ ] 🟡 **Lighthouse Accessibility**: ≥ 90

---

## 🔍 SEO (Básico)

### Técnico

- [ ] 🟡 **robots.txt**: Configurado corretamente
- [ ] 🟡 **sitemap.xml**: Gerado e atualizado
- [ ] 🟢 **Canonical URLs**: `<link rel="canonical">`

### Conteúdo

- [ ] 🟡 **Titles únicos**: Por página
- [ ] 🟡 **Meta descriptions**: Descritivas e únicas
- [ ] 🟢 **Structured data**: JSON-LD para organização

### Analytics

- [ ] 🟡 **Google Analytics**: Ou alternativa (Plausible, Umami)
- [ ] 🟢 **Error tracking**: Sentry configurado

---

## 🧪 Testes

### Unitários

- [ ] 🟡 **Componentes críticos**: Testados com Vitest/Jest
- [ ] 🟡 **Hooks customizados**: Testados isoladamente
- [ ] 🟢 **Coverage > 70%**: Para código crítico

### E2E

- [ ] 🔴 **Fluxo principal**: RF01→RF07 testado (Playwright)
- [ ] 🟡 **Login/Logout**: Testado
- [ ] 🟡 **Formulários críticos**: Solicitação, Aprovação
- [ ] 🟢 **Cross-browser**: Chrome, Firefox, Safari

### Visual

- [ ] 🟢 **Snapshot tests**: Componentes UI
- [ ] 🟢 **Visual regression**: Comparação de screenshots

---

## 📱 PWA (Opcional)

- [ ] 🟢 **manifest.json**: Nome, ícones, cores
- [ ] 🟢 **Service Worker**: Cache de assets
- [ ] 🟢 **Offline page**: Mensagem amigável
- [ ] 🟢 **Install prompt**: Adicionar à tela inicial

---

## 🚀 Deploy Checklist

### Pré-Deploy

- [ ] 🔴 **Build sem erros**: `npm run build` OK
- [ ] 🔴 **Variáveis de ambiente**: `.env.production` configurado
- [ ] 🔴 **API URL correta**: Apontando para produção
- [ ] 🟡 **Lighthouse local**: Scores aceitáveis

### Pós-Deploy

- [ ] 🔴 **Site acessível**: URL responde
- [ ] 🔴 **Login funciona**: Autenticação OK
- [ ] 🔴 **API conectada**: Dados carregando
- [ ] 🟡 **HTTPS ativo**: Certificado válido
- [ ] 🟡 **Console limpo**: Sem erros

### Monitoramento

- [ ] 🟡 **Uptime monitoring**: Pingdom, UptimeRobot
- [ ] 🟡 **Error tracking**: Sentry alertas
- [ ] 🟢 **Performance monitoring**: Web Vitals em produção

---

## 📚 Referências

- [Front-End Checklist](https://github.com/thedaviddias/Front-End-Checklist)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Web.dev Performance](https://web.dev/performance/)
- [Lighthouse Docs](https://developer.chrome.com/docs/lighthouse/)
- [React Performance](https://react.dev/learn/render-and-commit)

---

## Ferramentas Úteis

| Ferramenta | Uso |
|------------|-----|
| [Lighthouse](https://developers.google.com/web/tools/lighthouse) | Performance, A11y, SEO |
| [axe DevTools](https://www.deque.com/axe/devtools/) | Acessibilidade |
| [WebPageTest](https://www.webpagetest.org/) | Performance detalhada |
| [Bundlephobia](https://bundlephobia.com/) | Tamanho de dependências |
| [WAVE](https://wave.webaim.org/) | Acessibilidade visual |
| [GTmetrix](https://gtmetrix.com/) | Performance |
| [Security Headers](https://securityheaders.com/) | Headers de segurança |

---

*Última atualização: Janeiro 2026*
