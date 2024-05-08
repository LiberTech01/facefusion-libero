module.exports = () =>
{
	const config =
	{
		run:
		[
			{
				method: 'shell.run',
				params:
				{
					'message': 'git pull'
				}
			},
			{
				method: 'shell.run',
				params:
				{
					message: 'git pull --tags',
					path: 'facefusion'
				}
			},
			{
				method: 'shell.run',
				params:
				{
					message: 'git checkout 2.5.3',
					path: 'facefusion'
				}
			}
		]
	};

	return config;
};

