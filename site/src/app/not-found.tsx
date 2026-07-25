import Link from 'next/link'
export default function NotFound() {
  return (
    <div className="text-center py-20">
      <h2 className="text-xl font-bold mb-2">Not found</h2>
      <Link href="/" className="text-gold hover:text-rust">Home</Link>
    </div>
  )
}
