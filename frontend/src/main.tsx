import React from 'react'
import ReactDOM from 'react-dom/client'
import { createRootRoute, createRoute, createRouter, Link, Outlet, RouterProvider } from '@tanstack/react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@fontsource/dm-sans/latin-400.css'
import '@fontsource/dm-sans/latin-500.css'
import '@fontsource/dm-sans/latin-600.css'
import '@fontsource/space-grotesk/latin-500.css'
import '@fontsource/space-grotesk/latin-600.css'
import './styles/global.css'
import { Home } from './pages/Home'
import { Studio } from './pages/Studio'

const rootRoute = createRootRoute({
  component: () => <><a className="skip-link" href="#main">Skip to content</a><Outlet /></>,
  notFoundComponent: () => <main id="main" className="route-error"><span className="eyebrow">404 / OUT OF FRAME</span><h1>This page is out of the picture.</h1><Link to="/" className="button primary">Back to LumaLab</Link></main>,
  errorComponent: ({ reset }) => <main id="main" className="route-error"><h1>Something interrupted the view.</h1><p>Try loading this page again.</p><button className="button primary" onClick={reset}>Try again</button></main>,
})
const routeTree = rootRoute.addChildren([
  createRoute({ getParentRoute: () => rootRoute, path: '/', component: Home }),
  createRoute({ getParentRoute: () => rootRoute, path: '/studio', component: Studio }),
])
const router = createRouter({ routeTree, scrollRestoration: true })
declare module '@tanstack/react-router' { interface Register { router: typeof router } }
const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1 }, mutations: { retry: false } } })
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider></React.StrictMode>)
