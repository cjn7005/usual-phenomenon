import { MyTable } from './MyTable';

export function Customers() {
  return <MyTable 
    table_name={["Customer","Customers"]}
    url={"http://127.0.0.1:5000/customers/"}
    columns={["created_at", "customer_id", "email", "first_name", "last_name"]}
    column_names={["Created At", "Customer ID", "Email", "First Name", "Last Name"]}
    pk={"customer_id"}
    />
}

export function Addresses() {
  return <MyTable 
    table_name={["Address","Addresses"]}
    url={"http://127.0.0.1:5000/addresses/"}
    columns={["address_id", "customer_id", "line1", "city", "country"]}
    column_names={["Address ID", "Customer ID", "Line 1", "City", "Country"]}
    pk={"address_id"}
    />
}
