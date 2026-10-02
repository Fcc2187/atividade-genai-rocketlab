import { useState } from 'react'
import { Icon } from './Icon'

const examples = {
  'Finanças': { icon: 'bars', questions: ['Top 10 filmes com maior receita em R$', 'Filmes com maior margem de lucro, com receita e orçamento informados'] },
  'Popularidade': { icon: 'star', questions: ['Quais são os 5 filmes mais populares?', 'Nota média IMDb por ano de lançamento'] },
  'Elenco e equipe': { icon: 'people', questions: ['Ator com mais participações em filmes lançados nos últimos 5 anos', 'Diretores com maior nota média, com no mínimo 5 filmes'] },
  'Gêneros e produtoras': { icon: 'film', questions: ['Quantidade de filmes por gênero', 'Produtora com maior lucro total'] },
  'Avaliações': { icon: 'star', questions: ['Filmes mais avaliados pelos usuários', 'Filmes com maior divergência entre a nota média dos usuários e a nota IMDb'] },
} as const

export function Examples({ onChoose, disabled, auxiliary = false }: { onChoose: (question: string) => void; disabled: boolean; auxiliary?: boolean }) {
  const [category, setCategory] = useState<keyof typeof examples>('Popularidade')
  return <section className={`examples ${auxiliary ? 'examples-auxiliary' : ''}`} aria-label="Exemplos de perguntas">
    {auxiliary && <h2>Explore por categoria</h2>}
    <div className="category-list" role="group" aria-label="Categorias de exemplos">
      {(Object.keys(examples) as Array<keyof typeof examples>).map(name =>
        <button className="category-button" type="button" key={name} aria-pressed={category === name} onClick={() => setCategory(name)}>
          <Icon name={examples[name].icon} /><span>{name}</span>
        </button>)}
    </div>
    <div className="example-list">
      {examples[category].questions.map(question => <button type="button" className="example-button" key={question} disabled={disabled} onClick={() => onChoose(question)}>
        <span>{question}</span><Icon name="arrow" />
      </button>)}
    </div>
    {!auxiliary && <p className="small-note">Escolha um exemplo para preencher o campo. Você decide quando enviar.</p>}
  </section>
}
