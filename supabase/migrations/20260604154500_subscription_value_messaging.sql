update public.subscription_plans
set description = case id
    when 'free' then 'Pour explorer les tendances spatiales et valider l''interet du produit.'
    when 'pro' then 'Pour analyser, comparer et exporter les donnees utiles aux decisions.'
    when 'premium' then 'Pour anticiper les signaux faibles et transformer Artemis en cockpit de veille.'
    else description
end
where id in ('free', 'pro', 'premium');

delete from public.subscription_plan_features
where plan_id in ('free', 'pro', 'premium');

insert into public.subscription_plan_features (plan_id, feature, is_included, display_order)
values
    ('free', 'Vue d''ensemble des lancements et KPIs essentiels', true, 1),
    ('free', 'Briefing d''apercu pour comprendre les tendances majeures', true, 2),
    ('free', 'Analyses detaillees par pays, agence et periode', false, 3),
    ('free', 'Exports CSV pour travailler hors plateforme', false, 4),
    ('free', 'Signaux de veille et recommandations Premium', false, 5),
    ('pro', 'Dashboards complets avec lectures pays, agences et historique', true, 1),
    ('pro', 'Briefing avance avec angles d''analyse exploitables', true, 2),
    ('pro', 'Graphiques recommandes pour presenter rapidement les tendances', true, 3),
    ('pro', 'Exports CSV pour notebooks, reporting et analyses ML', true, 4),
    ('pro', 'Signaux de veille et recommandations Premium', false, 5),
    ('premium', 'Toutes les analyses Pro et exports CSV', true, 1),
    ('premium', 'Briefings enrichis pour lectures executives et editoriales', true, 2),
    ('premium', 'Signaux de veille sur ruptures de croissance et leaders emergents', true, 3),
    ('premium', 'Parcours recommande entre dashboards, carte et Space Race', true, 4),
    ('premium', 'Priorite aux futures couches ML et alertes avancees', true, 5);
