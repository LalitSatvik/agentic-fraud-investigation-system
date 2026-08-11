import * as React from "react"
import { useEffect, useRef } from "react"
import { createNoise2D } from "simplex-noise"

interface Point {
  x: number
  y: number
  wave: { x: number; y: number }
  cursor: { x: number; y: number; vx: number; vy: number }
}

interface WaveBackgroundProps {
  className?: string
  strokeColor?: string
  pointerSize?: number
  /**
   * Quiet mode: lower amplitude, no pointer tracking, no pointer dot — used
   * as a low-opacity background layer behind working screens (Dashboard,
   * Console). Omit for the full expressive hero treatment (Home).
   */
  ambient?: boolean
}

export function WaveBackground({
  className = "",
  strokeColor = "var(--ink)",
  pointerSize = 0.5,
  ambient = false,
}: WaveBackgroundProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const mouseRef = useRef({
    x: -10,
    y: 0,
    lx: 0,
    ly: 0,
    sx: 0,
    sy: 0,
    v: 0,
    vs: 0,
    a: 0,
    set: false,
  })
  const pathsRef = useRef<SVGPathElement[]>([])
  const linesRef = useRef<Point[][]>([])
  const noiseRef = useRef<((x: number, y: number) => number) | null>(null)
  const rafRef = useRef<number | null>(null)
  const boundingRef = useRef<DOMRect | null>(null)

  useEffect(() => {
    if (!containerRef.current || !svgRef.current) return
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return

    noiseRef.current = createNoise2D()
    setSize()
    setLines()

    window.addEventListener("resize", onResize)
    if (!ambient) {
      window.addEventListener("mousemove", onMouseMove)
      containerRef.current.addEventListener("touchmove", onTouchMove, { passive: false })
    }

    rafRef.current = requestAnimationFrame(tick)

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      window.removeEventListener("resize", onResize)
      window.removeEventListener("mousemove", onMouseMove)
      containerRef.current?.removeEventListener("touchmove", onTouchMove)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const setSize = () => {
    if (!containerRef.current || !svgRef.current) return
    boundingRef.current = containerRef.current.getBoundingClientRect()
    const { width, height } = boundingRef.current
    svgRef.current.style.width = `${width}px`
    svgRef.current.style.height = `${height}px`
  }

  const setLines = () => {
    if (!svgRef.current || !boundingRef.current) return
    const { width, height } = boundingRef.current
    linesRef.current = []

    pathsRef.current.forEach((path) => path.remove())
    pathsRef.current = []

    const gap = ambient ? 16 : 8
    const oWidth = width + 200
    const oHeight = height + 30
    const totalLines = Math.ceil(oWidth / gap)
    const totalPoints = Math.ceil(oHeight / gap)
    const xStart = (width - gap * totalLines) / 2
    const yStart = (height - gap * totalPoints) / 2

    for (let i = 0; i < totalLines; i++) {
      const points: Point[] = []
      for (let j = 0; j < totalPoints; j++) {
        points.push({
          x: xStart + gap * i,
          y: yStart + gap * j,
          wave: { x: 0, y: 0 },
          cursor: { x: 0, y: 0, vx: 0, vy: 0 },
        })
      }

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path")
      path.setAttribute("fill", "none")
      path.setAttribute("stroke", strokeColor)
      path.setAttribute("stroke-width", "1")
      svgRef.current!.appendChild(path)
      pathsRef.current.push(path)
      linesRef.current.push(points)
    }
  }

  const onResize = () => {
    setSize()
    setLines()
  }

  const onMouseMove = (e: MouseEvent) => updateMousePosition(e.pageX, e.pageY)

  const onTouchMove = (e: TouchEvent) => {
    e.preventDefault()
    const touch = e.touches[0]
    updateMousePosition(touch.clientX, touch.clientY)
  }

  const updateMousePosition = (x: number, y: number) => {
    if (!boundingRef.current) return
    const mouse = mouseRef.current
    mouse.x = x - boundingRef.current.left
    mouse.y = y - boundingRef.current.top + window.scrollY

    if (!mouse.set) {
      mouse.sx = mouse.x
      mouse.sy = mouse.y
      mouse.lx = mouse.x
      mouse.ly = mouse.y
      mouse.set = true
    }

    if (containerRef.current) {
      containerRef.current.style.setProperty("--x", `${mouse.sx}px`)
      containerRef.current.style.setProperty("--y", `${mouse.sy}px`)
    }
  }

  const movePoints = (time: number) => {
    const { current: lines } = linesRef
    const { current: mouse } = mouseRef
    const { current: noise } = noiseRef
    if (!noise) return

    const amplitude = ambient ? 3 : 8

    lines.forEach((points) => {
      points.forEach((p) => {
        const move =
          noise((p.x + time * 0.008) * 0.003, (p.y + time * 0.003) * 0.002) * amplitude

        p.wave.x = Math.cos(move) * (ambient ? 5 : 12)
        p.wave.y = Math.sin(move) * (ambient ? 3 : 6)

        if (ambient) return

        const dx = p.x - mouse.sx
        const dy = p.y - mouse.sy
        const d = Math.hypot(dx, dy)
        const l = Math.max(175, mouse.vs)

        if (d < l) {
          const s = 1 - d / l
          const f = Math.cos(d * 0.001) * s
          p.cursor.vx += Math.cos(mouse.a) * f * l * mouse.vs * 0.00035
          p.cursor.vy += Math.sin(mouse.a) * f * l * mouse.vs * 0.00035
        }

        p.cursor.vx += (0 - p.cursor.x) * 0.01
        p.cursor.vy += (0 - p.cursor.y) * 0.01
        p.cursor.vx *= 0.95
        p.cursor.vy *= 0.95
        p.cursor.x += p.cursor.vx
        p.cursor.y += p.cursor.vy
        p.cursor.x = Math.min(50, Math.max(-50, p.cursor.x))
        p.cursor.y = Math.min(50, Math.max(-50, p.cursor.y))
      })
    })
  }

  const moved = (point: Point, withCursorForce = true) => ({
    x: point.x + point.wave.x + (withCursorForce ? point.cursor.x : 0),
    y: point.y + point.wave.y + (withCursorForce ? point.cursor.y : 0),
  })

  const drawLines = () => {
    const { current: lines } = linesRef
    const { current: paths } = pathsRef

    lines.forEach((points, lIndex) => {
      if (points.length < 2 || !paths[lIndex]) return
      const first = moved(points[0], false)
      let d = `M ${first.x} ${first.y}`
      for (let i = 1; i < points.length; i++) {
        const current = moved(points[i])
        d += `L ${current.x} ${current.y}`
      }
      paths[lIndex].setAttribute("d", d)
    })
  }

  const tick = (time: number) => {
    const { current: mouse } = mouseRef
    mouse.sx += (mouse.x - mouse.sx) * 0.1
    mouse.sy += (mouse.y - mouse.sy) * 0.1

    const dx = mouse.x - mouse.lx
    const dy = mouse.y - mouse.ly
    const d = Math.hypot(dx, dy)

    mouse.v = d
    mouse.vs += (d - mouse.vs) * 0.1
    mouse.vs = Math.min(100, mouse.vs)
    mouse.lx = mouse.x
    mouse.ly = mouse.y
    mouse.a = Math.atan2(dy, dx)

    movePoints(time)
    drawLines()

    rafRef.current = requestAnimationFrame(tick)
  }

  return (
    <div
      ref={containerRef}
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
      style={{ "--x": "-0.5rem", "--y": "50%" } as React.CSSProperties}
    >
      <svg ref={svgRef} className="block h-full w-full" xmlns="http://www.w3.org/2000/svg" />
      {!ambient && (
        <div
          className="absolute left-0 top-0 rounded-full"
          style={{
            width: `${pointerSize}rem`,
            height: `${pointerSize}rem`,
            background: strokeColor,
            transform: "translate3d(calc(var(--x) - 50%), calc(var(--y) - 50%), 0)",
            willChange: "transform",
          }}
        />
      )}
    </div>
  )
}
