import '../App.css';
import { Table } from 'reactstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import { useEffect, useState } from 'react';

const BASE = "http://127.0.0.1:5000/customers/";
const COLUMNS = ["created_at","customer_id","email","first_name","last_name"];
const COLUMN_NAMES = ["Created At","Customer ID","Email","First Name","Last Name"];
const PK = "customer_id";

export function Module() {
    const [state, setState] = useState("loading");
    const [data, setData] = useState([]);

    async function getData() {
        try {
            let response = await fetch(BASE, { credentials: "include" });
            let dat = await response.json()
            if (!response.ok) {
                console.error(`Response status: ${response.status}`);
            }
            setData(dat);
            setState("loaded");
        } catch (error) {
            console.error(error);
        }
    }

    useEffect(() => { getData(); }, []);

    if (state !== "loading" && data.length > 0) {
        return (<Table hover striped>
            <thead>
                <tr>
                    <><th>{COLUMN_NAMES[COLUMNS.indexOf(PK)]}</th></>
                    {COLUMNS.map((k,i) => k == PK ? (<></>) : (<><td>{COLUMN_NAMES[i]}</td></>))}
                </tr>
            </thead>
            <tbody>
                {data.map((obj) => (<><tr>
                    <><th>{obj[PK]}</th></>
                    {COLUMNS.map((k) => k == PK ? (<></>) : (<><td>{obj[k]}</td></>))}
                </tr></>))}
            </tbody>
        </Table>);

    } else if (state == "loading") {
        return <>
            <h1>Loading...</h1>
        </>

    } else {
        return <>
            <h1>No data</h1>
        </>
    }

}