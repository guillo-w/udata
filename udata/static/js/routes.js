/**
 * Configure the router
 */
define(['jquery', 'router', 'logger'], function($, router, log) {

    var lang = $('html').attr('lang');

    function i18n(path) {
        return '/' + lang + path;
    }

    router.registerRoutes({
        home: {path: i18n('/'), moduleId: 'home'},
        metrics: {path: i18n('/metrics/'), moduleId: 'dashboard/site'},
        dashboard: {path: i18n('/dashboard/'), moduleId: 'dashboard/site'},
        map: {path: i18n('/map/'), moduleId: 'site/map'},
        search: {path: i18n('/search/'), moduleId: 'search'},

        // API Documentation
        apidoc: {path: i18n('/apidoc/*'), moduleId: 'apidoc'},
        apidoc_hash: {path: /\/\w+\.json(\/(get|post|put|delete|patch)_[\w_]+)?/, moduleId: 'apidoc'},

        // Site admin
        siteConfig: {path: i18n('/admin/site/'), moduleId: 'site/form'},
        siteTheme: {path: i18n('/admin/theme/'), moduleId: 'site/form'},
        siteIssues: {path: i18n('/admin/issues/'), moduleId: 'issue/list'},
        siteJobs: {path: i18n('/admin/jobs/'), moduleId: 'jobs/list'},

        // Datasets routes
        datasetSearch: {path: i18n('/datasets/'), moduleId: 'search'},
        datasetNew: {path: i18n('/datasets/new/'), moduleId: 'dataset/form'},
        datasetDisplay: {path: i18n('/datasets/:slug_or_id/'), moduleId: 'dataset/display'},
        datasetEdit: {path: i18n('/datasets/:slug_or_id/edit/'), moduleId: 'dataset/form'},
        datasetEditExtras: {path: i18n('/datasets/:slug_or_id/edit/extras/'), moduleId: 'form/extras'},
        datasetIssues: {path: i18n('/datasets/:slug_or_id/issues/'), moduleId: 'issue/list'},

        // Resources routes
        resourceNew: {path: i18n('/datasets/:slug_or_id/resources/new/'), moduleId: 'dataset/resource-form'},
        resourceEdit: {path: i18n('/datasets/:slug_or_id/resources/:rid/'), moduleId: 'dataset/resource-form'},

        // Community Resources routes
        communityResourceNew: {path: i18n('/datasets/:slug_or_id/community_resources/new/'), moduleId: 'dataset/resource-form'},
        communityResourceEdit: {path: i18n('/datasets/:slug_or_id/community_resources/:rid/'), moduleId: 'dataset/resource-form'},

        // Organizations routes
        orgSearch: {path: i18n('/organizations/'), moduleId: 'search'},
        orgNew: {path: i18n('/organizations/new/'), moduleId: 'organization/form'},
        orgDisplay: {path: i18n('/organizations/:slug_or_id/'), moduleId: 'organization/display'},
        orgEdit: {path: i18n('/organizations/:slug_or_id/edit/'), moduleId: 'organization/form'},
        orgMembers: {path: i18n('/organizations/:slug_or_id/edit/members/'), moduleId: 'organization/members'},
        orgRequests: {path: i18n('/organizations/:slug_or_id/edit/requests/'), moduleId: 'organization/membership-requests'},
        orgEditExtras: {path: i18n('/organizations/:slug_or_id/edit/extras/'), moduleId: 'form/extras'},
        orgIssues: {path: i18n('/organizations/:slug_or_id/issues/'), moduleId: 'issue/list'},
        orgDashboard: {path: i18n('/organizations/:slug_or_id/dashboard/'), moduleId: 'dashboard/organization'},

        // Reuses routes
        reuseSearch: {path: i18n('/reuses/'), moduleId: 'search'},
        reuseNew: {path: i18n('/reuses/new/'), moduleId: 'reuse/form'},
        reuseDisplay: {path: i18n('/reuses/:slug_or_id/'), moduleId: 'reuse/display'},
        reuseEdit: {path: i18n('/reuses/:slug_or_id/edit/'), moduleId: 'reuse/form'},
        reusesIssues: {path: i18n('/reuses/:slug_or_id/issues/'), moduleId: 'issue/list'},

        // User routes
        userSearch: {path: i18n('/users/'), moduleId: 'search'},
        userEdit: {path: i18n('/users/:slug_or_id/edit/'), moduleId: 'user/form'},
        userNotifications: {path: i18n('/users/:slug_or_id/edit/notifications/'), moduleId: 'user/notifications'},
        userEdit2: {path: i18n('/users/:slug_or_id/edit/*/'), moduleId: 'user/form'},
        userDisplay: {path: i18n('/users/:slug_or_id/'), moduleId: 'user/display'},
        userDisplay2: {path: i18n('/users/:slug_or_id/*/'), moduleId: 'user/display'},

        // Posts routes
        postNew: {path: i18n('/posts/new/'), moduleId: 'site/form'},
        postDisplay: {path: i18n('/posts/:slug_or_id/'), moduleId: 'post/display'},
        postEdit: {path: i18n('/posts/:slug_or_id/edit/'), moduleId: 'site/form'},

        // Topics routes
        topicNew: {path: i18n('/topics/new/'), moduleId: 'site/form'},
        topicDisplay: {path: i18n('/topics/:slug_or_id/'), moduleId: 'topic/display'},
        topicsEdit: {path: i18n('/topics/:slug_or_id/edit/'), moduleId: 'site/form'}
    })
    .on('routeload', function(module, routeArguments) {
        log.debug('Module "'+router.activeRoute.moduleId+'" loaded by route "'+router.activeRoute.path+'"');
        if (module && module.hasOwnProperty('start')) {
            log.debug('Starting module "'+router.activeRoute.moduleId+'" with parameters:', routeArguments);
            module.start();
        }
        log.debug('Module loaded');
    });

    return {
        start: function() {
            log.debug('Router starting');
            // Set up event handlers and trigger the initial page load
            router.init({
                // fireInitialStateChange: false
            });
            log.debug('Router started');
        }
    }
});
