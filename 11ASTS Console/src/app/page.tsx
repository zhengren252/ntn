'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function HomePage() {
  const router = useRouter()

  useEffect(() => {
    // 重定向到仪表盘
    router.push('/dashboard')
  }, [router])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-4">ASTS Console</h1>
        <p className="text-muted-foreground">正在跳转到仪表盘...</p>
      </div>
    </div>
  )
}