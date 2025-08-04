import type * as React from "react"
import { ChevronDown, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { BrandLogo } from "@/components/icons/brand-logo"

const NavItem = ({ children, hasDropdown = false }: { children: React.ReactNode; hasDropdown?: boolean }) => (
  <button className="flex items-center gap-1 text-gray-800 font-medium hover:text-blue-600 transition-colors">
    {children}
    {hasDropdown && <ChevronDown className="h-4 w-4" />}
  </button>
)

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full bg-white/80 backdrop-blur-sm">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-10">
            <a href="#" className="flex items-center gap-2">
              <BrandLogo className="h-8 w-8" />
              <span className="font-bold text-xl text-gray-800">brandbaston</span>
            </a>
            <nav className="hidden md:flex items-center gap-8">
              <NavItem hasDropdown>Solutions</NavItem>
              <NavItem hasDropdown>Customers</NavItem>
              <NavItem>Plans</NavItem>
              <NavItem hasDropdown>Resources</NavItem>
              <NavItem hasDropdown>About</NavItem>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" className="hidden md:inline-flex">
              <User className="h-5 w-5 text-gray-700" />
            </Button>
            <Button className="rounded-full bg-blue-600 hover:bg-blue-700 text-white font-bold">Book a Demo</Button>
          </div>
        </div>
      </div>
    </header>
  )
}
