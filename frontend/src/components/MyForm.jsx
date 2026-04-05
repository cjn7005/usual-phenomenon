import { Modal, ModalBody, ModalHeader, ModalFooter, Button, Form, FormGroup, Input, FormText, Label } from 'reactstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import { useEffect, useState } from 'react';

export function MyForm({isActive, onClosed, header, fields, obj, field_names, pk, onSubmit}) {
  const [isOpen, setIsOpen] = useState(false);
  const [formData, setFormData] = useState({});
  const [objPK, setObjPK] = useState(obj ? obj[pk] : null);

  useEffect(() => setObjPK(obj ? obj[pk] : null), [obj]);
  console.log(obj);
  console.log(objPK);
  useEffect(() => {setIsOpen(isActive)},[isActive]);
  
  function handleChange(e) {
    const { name, value } = e.target;

    setFormData({
      ...formData,
      [name]: value
    });
  };

  async function handleSubmit() {
    onSubmit(formData, objPK); 
    setIsOpen(false);
  }

  return (
  <Modal isOpen={isOpen} onClosed={() => {setFormData({}); onClosed();}}>
    <ModalHeader>
      {header}
    </ModalHeader>
    <Form onSubmit={(e) => {e.preventDefault(); handleSubmit();}}>
      <ModalBody>
        {fields.map((k,i) => (<>
          <FormGroup>
            <Label for={k}>{field_names[i]}</Label>
            <Input name={k} defaultValue={obj ? obj[k] : ""} onChange={(e) => handleChange(e)}/>
          </FormGroup>
        </>))}
      </ModalBody>
      <ModalFooter>
        <Button onClick={() => setIsOpen(false)}>Cancel</Button>
        <Button type="submit" color="success">Submit</Button>
      </ModalFooter>
    </Form>
  </Modal>  
  );
}