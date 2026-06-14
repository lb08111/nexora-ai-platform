/**
 * JotaDuo mascot (same as logo symbol). Used in Hero and Nav.
 */
import { CatPawIcon } from "./CatPawIcon";

interface JotaduoMascotProps {
  size?: number;
  className?: string;
}

export function JotaduoMascot({
  size = 80,
  className = "",
}: JotaduoMascotProps) {
  return <CatPawIcon size={size} className={className} />;
}
