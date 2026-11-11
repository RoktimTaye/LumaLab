import { useRef, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { ArrowUpRight, Menu, X } from 'lucide-react'
import { Brand } from './Brand'
import styles from './Shared.module.css'
export function Header() {
  const [open, setOpen] = useState(false)
  const trigger = useRef<HTMLButtonElement>(null)
  return <header className={styles.header} onKeyDown={e => { if (e.key === 'Escape' && open) { setOpen(false); trigger.current?.focus() } }}>
    <div className={`container ${styles.headerInner}`}><Brand />
      <nav className={`${styles.nav} ${open ? styles.open : ''}`} id="site-nav" aria-label="Main navigation">
        <Link to="/" onClick={() => setOpen(false)}>Home</Link><Link to="/studio">Studio</Link><a href="#features" onClick={() => setOpen(false)}>Features</a><a href="#about" onClick={() => setOpen(false)}>About</a>
        <Link to="/studio" className={styles.mobileCta}>Open Studio <ArrowUpRight size={16} /></Link>
      </nav>
      <Link to="/studio" className={`button primary ${styles.headerCta}`}>Open Studio <ArrowUpRight size={16} /></Link>
      <button ref={trigger} className={`icon-button ${styles.menu}`} onClick={() => setOpen(!open)} aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} aria-controls="site-nav">{open ? <X /> : <Menu />}</button>
    </div>
  </header>
}
