import { Link } from '@tanstack/react-router'
import styles from './Shared.module.css'
export function Brand() {
  return <Link to="/" className={styles.brand} aria-label="LumaLab home"><span className={styles.mark} aria-hidden="true"><i /><i /><i /><i /></span>LumaLab<span className={styles.brandDot}>®</span></Link>
}
