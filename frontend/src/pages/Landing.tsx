import { Hero } from '../components/Landing/Hero'
import { HowItWorks } from '../components/Landing/HowItWorks'
import { Architecture } from '../components/Landing/Architecture'
import { Pipeline } from '../components/Landing/Pipeline'
import { Highlights } from '../components/Landing/Highlights'
import { Comparison } from '../components/Landing/Comparison'
import { TechStack } from '../components/Landing/TechStack'
import { Performance } from '../components/Landing/Performance'
import { WalkthroughSection } from '../components/Landing/WalkthroughSection'
import { Footer } from '../components/Landing/Footer'
import { Navbar } from '../components/shared/Navbar'

export function Landing() {
  return (
    <>
      <Navbar />
      <Hero />
      <HowItWorks />
      <Architecture />
      <Pipeline />
      <Highlights />
      <Comparison />
      <TechStack />
      <Performance />
      <WalkthroughSection />
      <Footer />
    </>
  )
}
