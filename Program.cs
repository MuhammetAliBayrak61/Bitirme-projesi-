using Npgsql;
using System.Text.Json;
var builder = WebApplication.CreateBuilder(args);
var connection = builder.Configuration.GetConnectionString("Lst") ?? throw new InvalidOperationException("ConnectionStrings__Lst gerekli.");
builder.Services.AddSingleton(NpgsqlDataSource.Create(connection));
var app = builder.Build();
app.UseDefaultFiles();
app.UseStaticFiles();
app.MapGet("/api/iller", async (NpgsqlDataSource db, CancellationToken stop) =>
{
    await using var cmd = db.CreateCommand("SELECT name FROM province ORDER BY name");
    await using var rows = await cmd.ExecuteReaderAsync(stop);
    var names = new List<string>();
    while (await rows.ReadAsync(stop)) names.Add(rows.GetString(0));
    return Results.Ok(names);
});
app.MapGet("/api/iller/{name}", async (string name, NpgsqlDataSource db, CancellationToken stop) =>
{
    await using var cmd = db.CreateCommand("SELECT result::text FROM province WHERE name=$1");
    cmd.Parameters.AddWithValue(name);
    var result = await cmd.ExecuteScalarAsync(stop) as string;
    return result is null ? Results.NotFound() : Results.Text(result, "application/json");
});
app.MapGet("/api/konum", async (double lon, double lat, NpgsqlDataSource db, CancellationToken stop) =>
{
    if (!double.IsFinite(lon) || !double.IsFinite(lat) || Math.Abs(lat)>90 || Math.Abs(lon)>180)
        return Results.BadRequest();
    await using var cmd = db.CreateCommand("SELECT name FROM province WHERE ST_Covers(geom,ST_SetSRID(ST_MakePoint($1,$2),4326)) ORDER BY name LIMIT 1");
    cmd.Parameters.AddWithValue(lon); cmd.Parameters.AddWithValue(lat);
    var name = await cmd.ExecuteScalarAsync(stop);
    return name is string city ? Results.Ok(city) : Results.NotFound();
});
app.Run();
