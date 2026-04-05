import { Navbar } from 'reactstrap';
import {
	BrowserRouter as Router,
	Routes,
	Route,
	Navigate
} from "react-router-dom";

import { Customer, Address, Category, Product, Order, OrderItem, Payment, Shipment, Review, Supplier, ProductSupplier, Cart, CartItem, Discount, OrderDiscount, } from './components/Modules';

function App() {
	return <>
		<Router>
			<Navbar />
			<Routes>
				<Route exact path="/" element={<h1>It works!</h1>}/ >
				<Route path="/customers" element={<Customer />} />
				<Route path="/addresses" element={<Address />} />
				<Route path="/categories" element={<Category />} />
				<Route path="/products" element={<Product />} />
				<Route path="/orders" element={<Order />} />
				<Route path="/order_items" element={<OrderItem />} />
				<Route path="/payments" element={<Payment />} />
				<Route path="/shipments" element={<Shipment />} />
				<Route path="/reviews" element={<Review />} />
				<Route path="/suppliers" element={<Supplier />} />
				<Route path="/product_suppliers" element={<ProductSupplier />} />
				<Route path="/carts" element={<Cart />} />
				<Route path="/cart_items" element={<CartItem />} />
				<Route path="/discounts" element={<Discount />} />
				<Route path="/order_discounts" element={<OrderDiscount />} />
			</Routes>
		</Router>
	</>
}

export default App;
