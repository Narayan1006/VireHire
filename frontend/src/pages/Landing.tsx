import { Hero } from '../components/Landing/Hero'
import { Problem } from '../components/Landing/Problem'
import { Solution } from '../components/Landing/Solution'
import { HowItWorks } from '../components/Landing/HowItWorks'
import { Stats } from '../components/Landing/Stats'
import { CTA } from '../components/Landing/CTA'
import { Footer } from '../components/Landing/Footer'
import { Navbar } from '../components/shared/Navbar'

export function Landing() {
  return (
    <>
      <Navbar />
      <Hero />
      <Problem />
      <Solution />
      <HowItWorks />
      <Stats />
      <CTA />
      <Footer />
    </>
  )
}
