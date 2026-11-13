import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from '@tanstack/react-router'
import { ArrowUpRight } from 'lucide-react'
import { Brand } from './Brand'
import styles from './Shared.module.css'
export function Header() {
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const hash = useLocation({ select: location => location.hash })
  const trigger = useRef<HTMLButtonElement>(null)
  const header = useRef<HTMLElement>(null)

  useEffect(() => {
    const updateScroll = () => setScrolled(window.scrollY > 48)
    const desktop = window.matchMedia('(min-width: 1024px)')
    const closeOnDesktop = () => { if (desktop.matches) setOpen(false) }
    updateScroll()
    window.addEventListener('scroll', updateScroll, { passive: true })
    desktop.addEventListener('change', closeOnDesktop)
    return () => {
      window.removeEventListener('scroll', updateScroll)
      desktop.removeEventListener('change', closeOnDesktop)
    }
  }, [])

  useEffect(() => {
    if (!open) return
    const closeOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !header.current?.contains(event.target)) setOpen(false)
    }
    document.addEventListener('pointerdown', closeOutside)
    return () => document.removeEventListener('pointerdown', closeOutside)
  }, [open])

  return <header ref={header} className={`${styles.header} ${open ? styles.headerOpen : ''} ${scrolled ? styles.headerScrolled : ''}`}
    onKeyDown={event => {
      if (event.key === 'Escape' && open) { setOpen(false); trigger.current?.focus() }
    }}
    onBlur={event => {
      if (event.relatedTarget instanceof Node && !event.currentTarget.contains(event.relatedTarget)) setOpen(false)
    }}>
    <div className={styles.headerInner}><Brand />
      <nav className={`${styles.nav} ${open ? styles.open : ''}`} id="site-nav" aria-label="Main navigation">
        <Link to="/" activeOptions={{ exact: true, includeHash: true }} onClick={() => setOpen(false)}>Home</Link>
        <Link to="/studio" onClick={() => setOpen(false)}>Studio</Link>
        <a href="#features" aria-current={hash === 'features' ? 'location' : undefined} onClick={() => setOpen(false)}>Features</a>
        <a href="#about" aria-current={hash === 'about' ? 'location' : undefined} onClick={() => setOpen(false)}>About</a>
        <Link to="/studio" className={styles.mobileCta} onClick={() => setOpen(false)}>Open Studio <ArrowUpRight size={16} /></Link>
      </nav>
      <Link to="/studio" className={`button primary ${styles.headerCta}`}>Open Studio <ArrowUpRight size={16} /></Link>
      <button ref={trigger} className={styles.menu} onClick={() => setOpen(!open)} aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} aria-controls="site-nav"><span /><span /></button>
    </div>
  </header>
}
