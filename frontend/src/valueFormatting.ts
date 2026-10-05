import type { SQLValue } from './types'

const financial: Record<string, string> = {
  receita: 'Receita',
  bilheteria: 'Bilheteria',
  orcamento: 'Orçamento',
  lucro: 'Lucro',
  lucro_medio: 'Lucro médio',
  lucro_acumulado: 'Lucro acumulado',
  lucro_total: 'Lucro total',
  total_lucro: 'Lucro total',
}
const labels: Record<string, string> = {
  titulo: 'Título',
  titulo_filme: 'Título',
  filme: 'Filme',
  ano: 'Ano',
  ano_lancamento: 'Ano de lançamento',
  sk_movie_id: 'Identificador do filme',
  id_filme: 'Identificador do filme',
  url_poster: 'URL do pôster',
  poster: 'URL do pôster',
  popularidade: 'Popularidade',
  nota_imdb: 'Nota IMDb',
  nota_tmdb: 'Nota TMDB',
  nota_media_imdb: 'Nota média IMDb',
  nota_media_usuarios: 'Nota média dos usuários',
  qtd_avaliacoes_usuarios: 'Avaliações de usuários',
  margem_percentual: 'Margem (%)',
  margem_media_percentual: 'Margem média (%)',
  filmes: 'Filmes',
  filmes_validos: 'Filmes com dados válidos',
  filmes_totais: 'Total de filmes',
  nome_genero: 'Gênero',
  genero: 'Gênero',
  nome_pessoa: 'Pessoa',
  diretor: 'Diretor',
  ator: 'Ator',
  nome_produtora: 'Produtora',
  divergencia: 'Divergência de notas',
}
function currencyColumn(column: string) {
  const match = /^(.*)_(usd|brl)$/.exec(column)
  return match && financial[match[1]]
    ? { label: financial[match[1]], currency: match[2].toUpperCase() }
    : null
}
export function columnLabel(column: string): string {
  const name = column.trim().toLowerCase()
  const currency = currencyColumn(name)
  return currency
    ? `${currency.label} (${currency.currency})`
    : (labels[name] ?? column.replaceAll('_', ' '))
}
export function formatValue(
  value: SQLValue,
  column: string,
  compact = false,
): string {
  if (value === null) return 'Não informado'
  if (value === '') return 'Texto vazio'
  if (typeof value !== 'number') return value
  const name = column.trim().toLowerCase()
  if (
    ['ano', 'ano_lancamento', 'id_filme'].includes(name) ||
    name.endsWith('_id')
  )
    return String(value)
  const currency = currencyColumn(name)
  if (currency)
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: currency.currency,
      maximumFractionDigits: 2,
      ...(compact ? ({ notation: 'compact' } as const) : {}),
    }).format(value)
  if (['margem_percentual', 'margem_media_percentual'].includes(name))
    return (
      new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(
        value,
      ) + '%'
    )
  const rounded =
    name.startsWith('nota_') ||
    name === 'popularidade' ||
    name === 'divergencia'
  return new Intl.NumberFormat('pt-BR', {
    maximumFractionDigits: rounded ? 2 : 20,
  }).format(value)
}
