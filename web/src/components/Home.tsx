import { motion, cubicBezier } from "framer-motion"
import { WaveBackground } from "@/components/WaveBackground"
import { Button } from "@/components/ui/button"

interface HomeProps {
  onEnterDashboard: () => void
  onEnterConsole: () => void
}

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12, delayChildren: 0.1 } },
}

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: cubicBezier(0.16, 1, 0.3, 1) } },
}

export function Home({ onEnterDashboard, onEnterConsole }: HomeProps) {
  return (
    <div className="relative flex-1 overflow-y-auto">
      <div className="relative flex min-h-full flex-col items-center justify-center px-6 py-20 text-center">
        <WaveBackground className="opacity-70" />
        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="relative z-10 flex max-w-2xl flex-col items-center gap-6"
        >
          <motion.span variants={item} className="text-[13px] font-semibold text-ink-muted">
            Fraud Investigation Console
          </motion.span>
          <motion.h1
            variants={item}
            className="font-display text-5xl font-bold leading-[1.05] tracking-tight text-ink sm:text-6xl"
          >
            An agent investigates.
            <br />
            You decide.
          </motion.h1>
          <motion.p variants={item} className="max-w-lg text-base leading-relaxed text-ink-muted sm:text-lg">
            Every transaction that crosses the risk threshold gets a full investigation —
            device graphs, counterparty history, geo signals — argued into a recommendation.
            Nothing is final until a reviewer signs it.
          </motion.p>
          <motion.div variants={item} className="mt-2 flex flex-wrap items-center justify-center gap-3">
            <Button size="lg" onClick={onEnterConsole}>
              Open the queue
            </Button>
            <Button size="lg" variant="outline" onClick={onEnterDashboard}>
              View portfolio dashboard
            </Button>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}
