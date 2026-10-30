import { describe, expect, it } from 'vitest'
import { buildQuery } from './api.js'
import { colourFor, initials, money, runtime } from './format.js'

describe('format', () => {
  it('runtime', () => {
    expect(runtime(148)).toBe('2h 28m')
    expect(runtime(45)).toBe('45m')
  })
  it('initials', () => {
    expect(initials('The Dark Knight')).toBe('TD')
    expect(initials('Up')).toBe('U')
  })
  it('colour is stable', () => {
    expect(colourFor('Inception')).toBe(colourFor('Inception'))
  })
  it('money', () => {
    expect(money(292.57)).toBe('$293 M')
    expect(money(2787.97)).toBe('$2.79 B')
    expect(money(null)).toBe(null)
  })
  it('buildQuery repeats arrays', () => {
    expect(buildQuery({ genre: ['Drama', 'Crime'], q: '' })).toBe('?genre=Drama&genre=Crime')
  })
})
