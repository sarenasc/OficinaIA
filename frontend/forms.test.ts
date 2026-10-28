import { describe, it, expect } from 'vitest';
import { defaults, payload } from './forms';
describe('formularios de agentes', () => {
  it('mantiene permisos vacíos y prohíbe API externa por defecto', () => {
    const agent = defaults('agents', 'office-id');
    expect(agent.office_id).toBe('office-id');
    expect(agent.permissions).toEqual([]);
    expect(agent.external_policy).toBe('never');
    expect(agent.mode).toBe('safe');
  });
  it('rechaza JSON mal formado antes de enviarlo al backend', () => {
    expect(() =>
      payload('procedures', {
        name: 'P',
        office_id: 'O',
        description: '',
        steps: 'invalid',
      }),
    ).toThrow();
  });
});
