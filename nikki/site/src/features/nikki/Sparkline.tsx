import type {SparkPoint} from './types';
import styles from './nikki.module.css';

export default function Sparkline({points, positive}: {points: SparkPoint[]; positive: boolean}) {
  if (!points?.length) return null;
  const width = 180;
  const height = 48;
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || 1;
  const path = points.map((point, index) => {
    const x = (index / Math.max(1, points.length - 1)) * width;
    const y = height - ((point.value - min) / spread) * (height - 6) - 3;
    return (index === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1);
  }).join(' ');
  return (
    <svg className={styles.sparkline} viewBox={'0 0 ' + width + ' ' + height} role="img"
      aria-label={'90 日走势，从 ' + points[0].value.toFixed(2) + ' 到 ' + points[points.length - 1].value.toFixed(2)}>
      <path d={path} className={positive ? styles.sparkPositive : styles.sparkNegative} />
    </svg>
  );
}
