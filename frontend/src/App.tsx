import { useEffect, useState } from 'react';
import { supabase } from './utils/supabase';

type Todo = {
  id: string | number;
  name: string;
};

export default function App() {
  const [todos, setTodos] = useState<Todo[]>([]);

  useEffect(() => {
    async function getTodos() {
      const { data } = await supabase.from('todos').select();
      if (data) setTodos(data as Todo[]);
    }

    getTodos();
  }, []);

  return (
    <ul>
      {todos.map((todo) => (
        <li key={todo.id}>{todo.name}</li>
      ))}
    </ul>
  );
}
