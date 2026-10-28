import { Route, Routes } from 'react-router-dom'
import { Audit } from '../pages/Audit'
import { Home } from '../pages/Home'
import { Login } from '../pages/Login'
import { Lot } from '../pages/Lot'
import { Receipt } from '../pages/Receipt'
import { Register } from '../pages/Register'
import { Seller } from '../pages/Seller'
import { Wallet } from '../pages/Wallet'
import { Bids } from '../pages/Bids'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/seller" element={<Seller />} />
      <Route path="/wallet" element={<Wallet />} />
      <Route path="/bids" element={<Bids />} />
      <Route path="/lots/:id/audit" element={<Audit />} />
      <Route path="/lots/:id" element={<Lot />} />
      <Route path="/receipts/:id" element={<Receipt />} />
    </Routes>
  )
}
