# Whitelist de municípios — Região Metropolitana de Porto Alegre (RMPA)

A RMPA é oficialmente composta por 34 municípios (fonte: Metroplan/RS e IBGE).
Esta lista é usada em `pipeline/config.py` como filtro por **nome**, não por
código — o código oficial de município (`codigo_municipio`) é resolvido
dinamicamente pelo pipeline a partir da tabela de referência que a própria
Receita Federal distribui junto ao lote de dados (arquivo `F.K03200$Z.D*_MUNICCSV`).

> Importante: não fabricamos códigos de município manualmente — isso é uma
> fonte comum de erro silencioso (o código de Porto Alegre não é o mesmo em
> todas as tabelas de referência do governo). O pipeline sempre resolve o
> código consultando o arquivo oficial do próprio lote baixado.

Lista de referência (valide contra a fonte oficial do Metroplan antes da
ingestão final, pois municípios podem ser incluídos por lei estadual entre
uma consulta e outra):

Porto Alegre, Alvorada, Araricá, Arroio dos Ratos, Cachoeirinha, Campo Bom,
Canoas, Capela de Santana, Charqueadas, Dois Irmãos, Eldorado do Sul,
Estância Velha, Esteio, Glorinha, Gravataí, Guaíba, Igrejinha, Ivoti,
Montenegro, Nova Hartz, Nova Santa Rita, Novo Hamburgo, Parobé, Portão,
Rolante, Santo Antônio da Patrulha, Sapiranga, Sapucaia do Sul, São Jerônimo,
São Leopoldo, São Sebastião do Caí, Taquara, Triunfo, Viamão.

Fonte de consulta recomendada: http://www.metroplan.rs.gov.br
