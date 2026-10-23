import { login } from '../../../shared/auth/authClient';

export async function loginUser(username, password) {
  return login(username, password);
}
