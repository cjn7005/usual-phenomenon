import { Navbar } from 'reactstrap';
import { Customers, Addresses } from './components/Modules';
import {
    BrowserRouter as Router,
    Routes,
    Route,
    Navigate
} from "react-router-dom";

function App() {
  return <>
    <Router>
        <Navbar />
        <Routes>
            <Route exact path="/" element={<Navigate to="/customers" />}/>
            <Route path="/customers" element={<Customers />} />
            <Route path="/addresses" element={<Addresses />} />
        </Routes>
    </Router>
  </>
}

export default App;
