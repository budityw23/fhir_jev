/** Return a debounced function and retain its timer privately. */
export function debounce<T extends (...args: never[]) => void>(
  callback: T,
  waitMs: number,
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | undefined;
  return (...args) => {
    if (timer !== undefined) clearTimeout(timer);
    timer = setTimeout(() => callback(...args), waitMs);
  };
}
